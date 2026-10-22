import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.deps import require_admin
from app.core.config import get_settings
from app.models import User
from app.workers.outbox import hub

router = APIRouter(prefix="/events", tags=["events"])
TICKET_SECONDS = 60


@router.post("/ticket")
async def stream_ticket(admin: User = Depends(require_admin)):
    """EventSource cannot send Authorization headers: trade the bearer token for a 60s single-purpose ticket."""
    now = datetime.now(timezone.utc)
    t = jwt.encode(
        {"sub": str(admin.id), "cid": str(admin.company_id), "typ": "sse", "exp": now + timedelta(seconds=TICKET_SECONDS)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    return {"ticket": t, "expires_in": TICKET_SECONDS}


def company_from_ticket(ticket: str) -> str:
    try:
        c = jwt.decode(ticket, get_settings().jwt_secret, algorithms=["HS256"])
        if c.get("typ") != "sse":
            raise jwt.PyJWTError
        return c["cid"]
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(401, "Invalid or expired ticket")


async def event_stream(company_id: str, keepalive: float = 15.0):
    q = hub.subscribe(company_id)
    try:
        yield "retry: 3000\n\n"
        while True:
            try:
                ev = await asyncio.wait_for(q.get(), timeout=keepalive)
                yield f"id: {ev['id']}\nevent: {ev['type']}\ndata: {json.dumps(ev)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        hub.unsubscribe(company_id, q)


@router.get("/submissions")
async def submissions_stream(ticket: str = Query(...)):
    """Company-scoped: a connection only ever receives events of the company in its ticket.
    Events are a signal; clients must refetch authoritative data from the REST API."""
    cid = company_from_ticket(ticket)
    return StreamingResponse(
        event_stream(cid),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
