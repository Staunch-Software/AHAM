import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

_uuid = lambda: mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # noqa: E731
_ts = lambda **kw: mapped_column(DateTime(timezone=True), **kw)  # noqa: E731


class Submission(Base):
    __tablename__ = "form_submissions"
    __table_args__ = (
        UniqueConstraint("company_id", "idempotency_key"),
        Index("ix_sub_company_accepted", "company_id", "accepted_at_server"),
        Index("ix_sub_company_branch", "company_id", "branch_id"),
        Index("ix_sub_company_user", "company_id", "user_id"),
        UniqueConstraint("company_id", "root_id", "revision", name="uq_submission_root_revision"),
    )
    id: Mapped[uuid.UUID] = _uuid()  # canonical server submission ID
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    form_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_versions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(100))
    client_submission_id: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    answers: Mapped[dict] = mapped_column(JSONB)
    # Submission event, as reported by the device (never overwritten on retry).
    submitted_at_device: Mapped[datetime] = _ts()
    device_tz_offset_min: Mapped[int | None] = mapped_column(Integer)
    submission_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    submission_longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    submission_accuracy_m: Mapped[float | None] = mapped_column(Numeric(8, 2))
    submission_location_fix_at_device: Mapped[datetime | None] = _ts()
    submission_location_status: Mapped[str] = mapped_column(String(30), default="unavailable")
    # Human-readable place for the submission coordinates (reverse geocoded by the server, in the background).
    # place_status: pending | done | failed. Never replaces or alters the coordinates.
    submission_place_name: Mapped[str | None] = mapped_column(String(300))
    submission_place_status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending")
    submission_place_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Server events.
    received_at_server: Mapped[datetime] = _ts()
    accepted_at_server: Mapped[datetime] = _ts(server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="accepted")
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = _ts()
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    # A report is a chain of revisions. Revision 1 is what the agent first submitted; each correction after a
    # rejection is a NEW row (never an edit), sharing root_id and reference. Only the newest has is_latest = true.
    root_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    corrects_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reference: Mapped[str | None] = mapped_column(String(30), index=True)  # e.g. FS-2026-0042
    # Denormalised copy of the latest review decision (the full history is in submission_reviews).
    review_reason_code: Mapped[str | None] = mapped_column(String(50))
    review_comment: Mapped[str | None] = mapped_column(Text)
    review_flags: Mapped[list | None] = mapped_column(JSONB)
    # Labels of managed options (e.g. type of person) as they were when the report was accepted.
    option_labels: Mapped[dict | None] = mapped_column(JSONB)


class SubmissionPhoto(Base):
    """Photo ID is chosen by the client and is stable across retries."""

    __tablename__ = "submission_photos"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("form_submissions.id"), index=True
    )
    group_key: Mapped[str | None] = mapped_column(String(100))  # repeatable-entry id
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


class SubmissionEvent(Base):
    __tablename__ = "submission_events"
    id: Mapped[uuid.UUID] = _uuid()
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_submissions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str | None] = mapped_column(Text)
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
