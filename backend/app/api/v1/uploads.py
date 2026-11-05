import io
import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from PIL import ExifTags, Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_perm
from app.core.config import get_settings
from app.core.db import get_session
from app.models import Photo, SankalpEntry, User
from app.services.scope import entry_scope
from app.storage.base import get_storage, sign_file_url, verify_file_sig

router = APIRouter(tags=["photos"])
require_agent = require_perm("entries.create")

ALLOWED_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
LocationStatus = Literal["obtained", "permission_denied", "services_disabled", "timeout", "unavailable"]
_RANGE = re.compile(r"^bytes (\d+)-(\d+)/(\d+)$")


class InitiateIn(BaseModel):
    photo_id: uuid.UUID
    filename: str | None = Field(None, max_length=255)
    mime_type: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    photo_captured_at_device: datetime | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    accuracy_m: float | None = Field(None, ge=0, le=100000)
    location_fix_at_device: datetime | None = None
    location_status: LocationStatus = "unavailable"
    location_source: str | None = Field(None, max_length=30)


def _state(p: Photo) -> dict:
    return {
        "photo_id": str(p.id),
        "upload_status": p.upload_status,
        "received_bytes": get_storage().part_size(str(p.id)) if p.upload_status != "complete" else p.size_bytes,
    }


async def _own_photo(s: AsyncSession, photo_id: uuid.UUID, user: User) -> Photo:
    p = await s.get(Photo, photo_id)
    if not p or p.company_id != user.company_id or p.user_id != user.id:
        raise HTTPException(404, "Not found")
    return p


@router.post("/uploads/initiate")
async def initiate(body: InitiateIn, user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)):
    if body.mime_type not in ALLOWED_MIME:
        raise HTTPException(422, "Unsupported image type")
    if body.size_bytes > get_settings().max_upload_bytes:
        raise HTTPException(413, "File too large")
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(422, "latitude and longitude must be provided together")
    existing = await s.get(Photo, body.photo_id)
    if existing:
        # Idempotent re-initiate by the same agent with the same content; anything else is a conflict.
        if (existing.company_id, existing.user_id) != (user.company_id, user.id) or (
            existing.expected_sha256 != body.sha256.lower()
        ):
            raise HTTPException(409, "photo_id already in use")
        return _state(existing)
    has_fix = body.latitude is not None
    p = Photo(
        id=body.photo_id, company_id=user.company_id, user_id=user.id,
        original_filename=body.filename, mime_type=body.mime_type,
        expected_size=body.size_bytes, expected_sha256=body.sha256.lower(),
        photo_captured_at_device=body.photo_captured_at_device,
        photo_capture_latitude=body.latitude, photo_capture_longitude=body.longitude,
        photo_capture_accuracy_m=body.accuracy_m,
        photo_location_fix_at_device=body.location_fix_at_device,
        photo_location_status="obtained" if has_fix else (
            body.location_status if body.location_status != "obtained" else "unavailable"),
        location_source=body.location_source if has_fix else None,
    )
    s.add(p)
    await s.commit()
    return _state(p)


@router.get("/uploads/{photo_id}")
async def upload_status(photo_id: uuid.UUID, user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)):
    return _state(await _own_photo(s, photo_id, user))


@router.put("/uploads/{photo_id}")
async def upload_bytes(
    photo_id: uuid.UUID, request: Request, user: User = Depends(require_agent),
    s: AsyncSession = Depends(get_session),
):
    """Raw body. Optional `Content-Range: bytes start-end/total` for resumable chunks."""
    p = await _own_photo(s, photo_id, user)
    if p.upload_status == "complete":
        return _state(p)
    body = await request.body()
    offset = 0
    if (cr := request.headers.get("content-range")):
        m = _RANGE.match(cr)
        if not m or int(m[3]) != p.expected_size or int(m[2]) - int(m[1]) + 1 != len(body):
            raise HTTPException(400, "Bad Content-Range")
        offset = int(m[1])
    if offset + len(body) > p.expected_size:
        raise HTTPException(413, "Exceeds declared size")
    try:
        get_storage().append_part(str(p.id), offset, body)
    except ValueError:
        raise HTTPException(409, detail={"message": "offset mismatch", **_state(p)})
    p.upload_status = "uploading"
    await s.commit()
    return _state(p)


def _exif_datetime(img: Image.Image) -> datetime | None:
    try:
        exif = img.getexif()
        raw = exif.get_ifd(ExifTags.IFD.Exif).get(36867) or exif.get(306)  # DateTimeOriginal / DateTime
        if raw:
            # EXIF has no timezone; stored as UTC-labelled naive value, treated as a hint only.
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None
    return None


@router.post("/uploads/{photo_id}/complete")
async def complete(photo_id: uuid.UUID, user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)):
    p = await _own_photo(s, photo_id, user)
    if p.upload_status == "complete":
        return _state(p)
    store = get_storage()
    pid = str(p.id)
    if store.part_size(pid) == 0:
        raise HTTPException(409, detail={"message": "no data received", **_state(p)})
    digest, size = store.part_sha256(pid)
    if size != p.expected_size:
        raise HTTPException(409, detail={"message": "incomplete upload", **_state(p)})
    if digest != p.expected_sha256:
        store.discard_part(pid)  # corrupt: client must re-upload from byte 0
        p.upload_status = "pending"
        await s.commit()
        raise HTTPException(422, "Checksum mismatch; upload discarded, please re-upload")
    # Verify it is really an image of the declared type, then build a metadata-free thumbnail.
    data = store.read_part(pid)
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        fmt_ok = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(img.format)
        if fmt_ok != p.mime_type:
            raise ValueError("type mismatch")
        p.exif_captured_at = _exif_datetime(img)
        thumb = img.convert("RGB")
        thumb.thumbnail((320, 320))
        buf = io.BytesIO()
        thumb.save(buf, "JPEG", quality=80)  # re-encoded: no EXIF/GPS carried over
    except (UnidentifiedImageError, ValueError, OSError):
        store.discard_part(pid)
        p.upload_status = "pending"
        await s.commit()
        raise HTTPException(422, "File is not a valid image of the declared type")
    now = datetime.now(timezone.utc)
    ext = ALLOWED_MIME[p.mime_type]
    key = f"{p.company_id}/{now:%Y/%m}/{pid}.{ext}"
    thumb_key = f"{p.company_id}/{now:%Y/%m}/{pid}.thumb.jpg"
    store.finalize(pid, key)
    store.put(thumb_key, buf.getvalue())
    p.storage_key, p.thumb_key, p.size_bytes, p.sha256 = key, thumb_key, size, digest
    p.upload_status, p.upload_completed_at_server = "complete", now
    await s.commit()
    return _state(p)


# ---- Authorized viewing ----
async def _viewable(s: AsyncSession, photo_id: uuid.UUID, user: User) -> Photo:
    """The SO who took it, or anyone whose scope includes the entry it belongs to."""
    p = await s.get(Photo, photo_id)
    if not p or p.company_id != user.company_id or p.upload_status != "complete":
        raise HTTPException(404, "Not found")
    if p.user_id == user.id:
        return p
    if p.entry_id and (await s.execute(select(SankalpEntry.id).where(
            SankalpEntry.id == p.entry_id, await entry_scope(s, user)))).first():
        return p
    raise HTTPException(404, "Not found")


@router.get("/photos/{photo_id}/url")
async def photo_url(photo_id: uuid.UUID, user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    p = await _viewable(s, photo_id, user)
    return {"url": sign_file_url(str(p.id), "original"), "thumb_url": sign_file_url(str(p.id), "thumb")}


@router.get("/files/{photo_id}", include_in_schema=False)
async def file(
    photo_id: uuid.UUID, exp: int, sig: str, variant: Literal["original", "thumb"] = "original",
    s: AsyncSession = Depends(get_session),
):
    if not verify_file_sig(str(photo_id), variant, exp, sig):
        raise HTTPException(403, "Link expired or invalid")
    p = await s.get(Photo, photo_id)
    if not p or p.upload_status != "complete":
        raise HTTPException(404, "Not found")
    key, mime = (p.thumb_key, "image/jpeg") if variant == "thumb" else (p.storage_key, p.mime_type)
    return Response(get_storage().read(key), media_type=mime, headers={"Cache-Control": "private, max-age=60"})