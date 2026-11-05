"""Background worker that fills in place names for photo and entry coordinates.

Picks rows that have coordinates and status 'pending', asks the geocoder, stores the name (status 'done'). A failed
or empty lookup counts as an attempt; after MAX_ATTEMPTS the row is 'failed' (coordinates still shown, just no name).
Safe to run next to the API: rows are claimed with FOR UPDATE SKIP LOCKED.
"""
import asyncio
import logging

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Photo, SankalpEntry
from app.services.geocoding import Geocoder, get_geocoder

log = logging.getLogger("fieldsync.geocode")
MAX_ATTEMPTS = 3

# (model, latitude, longitude, name, status, attempts) attribute names
_TARGETS = [
    (Photo, "photo_capture_latitude", "photo_capture_longitude", "photo_place_name", "photo_place_status", "photo_place_attempts"),
    (SankalpEntry, "latitude", "longitude", "place_name", "place_status", "place_attempts"),
]


async def geocode_once(geocoder: Geocoder, batch: int = 5) -> int:
    """Processes up to `batch` pending rows per table; returns how many rows were looked at."""
    looked = 0
    async with SessionLocal() as s:
        for model, lat_a, lon_a, name_a, status_a, att_a in _TARGETS:
            rows = (
                await s.execute(
                    select(model)
                    .where(getattr(model, lat_a).is_not(None), getattr(model, lon_a).is_not(None), getattr(model, status_a) == "pending")
                    .limit(batch)
                    .with_for_update(skip_locked=True)
                )
            ).scalars().all()
            for row in rows:
                looked += 1
                name = None
                try:
                    name = await geocoder.reverse(float(getattr(row, lat_a)), float(getattr(row, lon_a)))
                except Exception as e:  # noqa: BLE001 - network/provider errors must never kill the worker
                    log.warning("geocoding failed", extra={"error": str(e)[:200]})
                if name:
                    setattr(row, name_a, name[:300])
                    setattr(row, status_a, "done")
                else:
                    attempts = getattr(row, att_a) + 1
                    setattr(row, att_a, attempts)
                    if attempts >= MAX_ATTEMPTS:
                        setattr(row, status_a, "failed")
        await s.commit()
    return looked


async def run_geocode_worker(stop: asyncio.Event) -> None:
    geocoder = get_geocoder()
    if geocoder is None:
        return
    while not stop.is_set():
        try:
            n = await geocode_once(geocoder)
        except Exception:  # noqa: BLE001
            log.exception("geocode worker iteration failed")
            n = 0
        await asyncio.sleep(0.5 if n else 3.0)
