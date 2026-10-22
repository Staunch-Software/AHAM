import io
import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from PIL import ExifTags, Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_roles
from app.core.config import get_settings
from app.core.db import get_session
from app.models import Submission, SubmissionPhoto, SubmissionPhotoLink, User
from app.services.geocoding import place_status_for_api
from app.storage.base import get_storage, sign_file_url, verify_file_sig

router = APIRouter(tags=["photos"])
require_agent = require_roles("agent")

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


def _state(p: SubmissionPhoto) -> dict:
    return {
        "photo_id": str(p.id),
        "upload_status": p.upload_status,
        "received_bytes": get_storage().part_size(str(p.id)) if p.upload_status != "complete" else p.size_bytes,
    }


async def _own_photo(s: AsyncSession, photo_id: uuid.UUID, user: User) -> SubmissionPhoto:
    p = await s.get(SubmissionPhoto, photo_id)
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
    existing = await s.get(SubmissionPhoto, body.photo_id)
    if existing:
        # Idempotent re-initiate by the same agent with the same content; anything else is a conflict.
        if (existing.company_id, existing.user_id) != (user.company_id, user.id) or (
            existing.expected_sha256 != body.sha256.lower()
        ):
            raise HTTPException(409, "photo_id already in use")
        return _state(existing)
    has_fix = body.latitude is not None
    p = SubmissionPhoto(
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
async def _viewable(s: AsyncSession, photo_id: uuid.UUID, user: User) -> SubmissionPhoto:
    p = await s.get(SubmissionPhoto, photo_id)
    if not p or p.company_id != user.company_id or p.upload_status != "complete":
        raise HTTPException(404, "Not found")
    if user.role != "admin" and p.user_id != user.id:
        raise HTTPException(404, "Not found")
    return p


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
    p = await s.get(SubmissionPhoto, photo_id)
    if not p or p.upload_status != "complete":
        raise HTTPException(404, "Not found")
    key, mime = (p.thumb_key, "image/jpeg") if variant == "thumb" else (p.storage_key, p.mime_type)
    return Response(get_storage().read(key), media_type=mime, headers={"Cache-Control": "private, max-age=60"})


@router.get("/submissions/{submission_id}/photos")
async def submission_photos(
    submission_id: uuid.UUID, user: User = Depends(current_user), s: AsyncSession = Depends(get_session)
):
    sub = await s.get(Submission, submission_id)
    if not sub or sub.company_id != user.company_id or (user.role != "admin" and sub.user_id != user.id):
        raise HTTPException(404, "Not found")
    pairs = (
        await s.execute(
            select(SubmissionPhoto, SubmissionPhotoLink)
            .join(SubmissionPhotoLink, SubmissionPhotoLink.photo_id == SubmissionPhoto.id)
            .where(SubmissionPhotoLink.submission_id == submission_id)
        )
    ).all()
    return [photo_dict(p, link) for p, link in pairs]


def _f(v):
    return None if v is None else float(v)


def photo_dict(p: SubmissionPhoto, link: SubmissionPhotoLink | None = None) -> dict:
    return {
        "photo_id": str(p.id), "group_key": link.group_key if link else p.group_key,
        "field_key": link.field_key if link else p.field_key,
        "original_filename": p.original_filename, "mime_type": p.mime_type, "size_bytes": p.size_bytes,
        "sha256": p.sha256, "upload_status": p.upload_status,
        "photo_captured_at_device": p.photo_captured_at_device, "exif_captured_at": p.exif_captured_at,
        "photo_capture_latitude": _f(p.photo_capture_latitude),
        "photo_capture_longitude": _f(p.photo_capture_longitude),
        "photo_capture_accuracy_m": _f(p.photo_capture_accuracy_m),
        "photo_location_fix_at_device": p.photo_location_fix_at_device,
        "photo_location_status": p.photo_location_status, "location_source": p.location_source,
        "photo_place_name": p.photo_place_name, "photo_place_status": place_status_for_api(p.photo_place_status),
        "upload_completed_at_server": p.upload_completed_at_server,
        "url": sign_file_url(str(p.id), "original"), "thumb_url": sign_file_url(str(p.id), "thumb"),
    }
