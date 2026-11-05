"""Transactional-outbox publisher + in-process SSE hub.

Events are written to `transactional_outbox` in the same transaction as the submission.
The worker delivers them to connected SSE clients and marks them processed; failures are
retried with exponential backoff. The hub is in-process: run a single API worker process, or
replace `Hub` with a shared bus (e.g. Postgres LISTEN/NOTIFY) before scaling horizontally.
"""
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import OutboxEvent

log = logging.getLogger("fieldsync.outbox")


class Hub:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, company_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subs[company_id].add(q)
        return q

    def unsubscribe(self, company_id: str, q: asyncio.Queue) -> None:
        self._subs[company_id].discard(q)

    def publish(self, company_id: str, event: dict) -> int:
        n = 0
        for q in list(self._subs.get(company_id, ())):
            try:
                q.put_nowait(event)
                n += 1
            except asyncio.QueueFull:  # slow client: it will refetch on reconnect
                self._subs[company_id].discard(q)
        return n


hub = Hub()
wakeup = asyncio.Event()


def notify_outbox() -> None:
    wakeup.set()


async def process_outbox_once(batch: int = 50) -> int:
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(OutboxEvent)
                .where(OutboxEvent.processed_at.is_(None), OutboxEvent.next_attempt_at <= datetime.now(timezone.utc))
                .order_by(OutboxEvent.id)
                .limit(batch)
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
        for ev in rows:
            try:
                hub.publish(
                    str(ev.company_id),
                    {"id": ev.id, "type": ev.event_type, **ev.payload},
                )
                ev.processed_at = datetime.now(timezone.utc)
            except Exception as e:  # noqa: BLE001
                ev.attempts += 1
                ev.last_error = str(e)[:500]
                ev.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=min(2**ev.attempts, 300))
                log.exception("outbox publish failed", extra={"outbox_id": ev.id})
        await s.commit()
        return len(rows)


async def run_worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            n = await process_outbox_once()
        except Exception:  # noqa: BLE001
            log.exception("outbox worker iteration failed")
            n = 0
        if n == 0:
            try:
                await asyncio.wait_for(wakeup.wait(), timeout=1.0)  # woken on commit, polls as fallback
            except asyncio.TimeoutError:
                pass
            wakeup.clear()
