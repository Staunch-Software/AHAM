"""Queue every stored location for a fresh place-name lookup (for example after switching GEOCODER to google).

    python -m app.regeocode            # all photos and submissions that have coordinates

The running API's background worker then re-looks them up (about 1 request/second for nominatim; as fast as Google
allows). Existing names stay visible until replaced. Coordinates are never touched.
"""
import asyncio

from sqlalchemy import update

from app.core.db import SessionLocal
from app.models import Submission, SubmissionPhoto


async def main() -> None:
    async with SessionLocal() as s:
        p = await s.execute(
            update(SubmissionPhoto).where(SubmissionPhoto.photo_capture_latitude.is_not(None))
            .values(photo_place_status="pending", photo_place_attempts=0))
        q = await s.execute(
            update(Submission).where(Submission.submission_latitude.is_not(None))
            .values(submission_place_status="pending", submission_place_attempts=0))
        await s.commit()
    print(f"Queued {p.rowcount} photo locations and {q.rowcount} submission locations for a new place-name lookup.")


if __name__ == "__main__":
    asyncio.run(main())
