import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

_ts = lambda **kw: mapped_column(DateTime(timezone=True), **kw)  # noqa: E731


class Photo(Base):
    """An evidence photo. The ID is chosen by the client and is stable across retries.

    Uploaded on its own (resumable), then attached to a Sankalp entry when the entry is submitted.
    `submission_id` / `group_key` / `field_key` belong to the retired form reports and are kept for old rows.
    """

    __tablename__ = "submission_photos"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    entry_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sankalp_entries.id"), index=True)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    group_key: Mapped[str | None] = mapped_column(String(100))
    field_key: Mapped[str | None] = mapped_column(String(100))
    storage_key: Mapped[str | None] = mapped_column(String(300))
    thumb_key: Mapped[str | None] = mapped_column(String(300))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(50))
    expected_size: Mapped[int] = mapped_column(BigInteger)
    expected_sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    # Capture event (device-reported, at the moment the photo was taken).
    photo_captured_at_device: Mapped[datetime | None] = _ts()
    exif_captured_at: Mapped[datetime | None] = _ts()  # read from the file; kept separate
    photo_capture_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    photo_capture_longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    photo_capture_accuracy_m: Mapped[float | None] = mapped_column(Numeric(8, 2))
    photo_location_fix_at_device: Mapped[datetime | None] = _ts()
    photo_location_status: Mapped[str] = mapped_column(String(30), default="unavailable")
    photo_place_name: Mapped[str | None] = mapped_column(String(300))
    photo_place_status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending")
    photo_place_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    location_source: Mapped[str | None] = mapped_column(String(30))
    upload_status: Mapped[str] = mapped_column(String(20), default="pending")
    upload_completed_at_server: Mapped[datetime | None] = _ts()
    created_at: Mapped[datetime] = _ts(server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "transactional_outbox"
    __table_args__ = (Index("ix_outbox_pending", "next_attempt_at", postgresql_where="processed_at IS NULL"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _ts(server_default=func.now())
    processed_at: Mapped[datetime | None] = _ts()
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = _ts(server_default=func.now())
    last_error: Mapped[str | None] = mapped_column(Text)
