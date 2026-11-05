"""Queue every stored location for a fresh place-name lookup (for example after switching GEOCODER to google).

    python -m app.regeocode            # all photos and entries that have coordinates

The running API's background worker then re-looks them up (about 1 request/second for nominatim; as fast as Google
allows). Existing names stay visible until replaced. Coordinates are never touched.
"""
import asyncio

from sqlalchemy import update

from app.core.db import SessionLocal
from app.models import Photo, SankalpEntry


async def main() -> None:
    async with SessionLocal() as s:
        p = await s.execute(
            update(Photo).where(Photo.photo_capture_latitude.is_not(None))
            .values(photo_place_status="pending", photo_place_attempts=0))
        q = await s.execute(
            update(SankalpEntry).where(SankalpEntry.latitude.is_not(None))
            .values(place_status="pending", place_attempts=0))
        await s.commit()
    print(f"Queued {p.rowcount} photo locations and {q.rowcount} entry locations for a new place-name lookup.")


if __name__ == "__main__":
    asyncio.run(main())
