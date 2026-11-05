"""Once-a-day work per company: the automatic selection run (if Settings > auto_selection_time is set), and
closing actions whose window has passed (which can change an entry's RAG). Safe next to manual runs: the selection
takes a per-company lock and only adds what is missing."""
import asyncio
import logging
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Company, SelectionRun
from app.services.periods import tz_of
from app.services.sankalp.ops import recompute_time_based, run_selection
from app.services.settings import load_settings

log = logging.getLogger("fieldsync.daily")
_expired_done: dict[uuid.UUID, date] = {}


async def daily_once(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    async with SessionLocal() as s:
        companies = (await s.execute(select(Company).where(Company.status == "active"))).scalars().all()
    for co in companies:
        local = now.astimezone(tz_of(co.timezone))
        today = local.date()
        async with SessionLocal() as s:
            cfg = await load_settings(s, co.id)
            if cfg.auto_selection_time and local.time() >= time.fromisoformat(cfg.auto_selection_time):
                ran = (await s.execute(select(SelectionRun.id).where(SelectionRun.company_id == co.id,
                                                                     SelectionRun.run_date == today).limit(1))).first()
                if not ran:
                    result = await run_selection(s, co.id, today, None)
                    await s.commit()
                    log.info("automatic selection run", extra={"company": co.code, "result": str(result)[:500]})
            if _expired_done.get(co.id) != today:
                n = await recompute_time_based(s, co.id)
                await s.commit()
                _expired_done[co.id] = today
                if n:
                    log.info("expired actions closed", extra={"company": co.code, "entries": n})


async def run_daily_worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await daily_once()
        except Exception:  # noqa: BLE001 - never let the loop die
            log.exception("daily worker iteration failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
