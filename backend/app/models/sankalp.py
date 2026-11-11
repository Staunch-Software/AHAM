"""The Sankalp entry (one per person an SO meets) and its history."""
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


_ts = lambda **kw: mapped_column(DateTime(timezone=True), **kw)  # noqa: E731


class SankalpEntry(Base):
    """Section 4 of the business logic. `entry_code` is the permanent Entry ID; every later step keys on it.

    Who made the entry (Emp ID, branch, spoke) comes from the roster of the signed-in SO, never from the request.
    The entry's time is the device's Submit press, so an entry made offline keeps the time it was really made.
    The "calling state" columns are derived: services.sankalp.recompute() refreshes them after every event.
    """

    __tablename__ = "sankalp_entries"
    __table_args__ = (
        UniqueConstraint("company_id", "entry_code", name="uq_entry_code"),
        UniqueConstraint("company_id", "idempotency_key", name="uq_entry_idempotency"),
        Index("ix_entry_company_phone", "company_id", "phone"),
        Index("ix_entry_company_so_date", "company_id", "so_user_id", "entry_date"),
        Index("ix_entry_company_branch_date", "company_id", "branch_id", "entry_date"),
        Index("ix_entry_company_count_date", "company_id", "count_date"),
    )
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    entry_code: Mapped[str] = mapped_column(String(60))
    emp_code: Mapped[str] = mapped_column(String(50))  # the Emp ID the Entry ID was built from; never changes
    so_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))  # current SO (13.1 can change it)
    original_so_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    # The branch that works the lead (7.4 "handling branch"); None = the SO's branch. Credit stays with branch_id.
    work_branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    spoke: Mapped[str | None] = mapped_column(String(100))
    # What was met
    category: Mapped[str] = mapped_column(String(30))  # app.services.sankalp.rules.CATEGORIES
    cp_subtype_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cp_subtypes.id"))
    cp_subtype_label: Mapped[str | None] = mapped_column(String(100))  # as it was when the entry was made
    person_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(10))  # cleaned, always valid ([6-9]\d{9})
    phone_raw: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    keka_photo_time: Mapped[time | None] = mapped_column(Time)
    # When and where (device-reported at the Submit press)
    submitted_at_device: Mapped[datetime] = _ts()
    device_tz_offset_min: Mapped[int | None] = mapped_column(Integer)
    entry_date: Mapped[date] = mapped_column(Date)
    count_date: Mapped[date] = mapped_column(Date)
    device_time_suspect: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    accuracy_m: Mapped[float | None] = mapped_column(Numeric(8, 2))
    location_fix_at_device: Mapped[datetime | None] = _ts()
    location_status: Mapped[str] = mapped_column(String(30), default="unavailable")
    place_name: Mapped[str | None] = mapped_column(String(300))
    place_status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending")
    place_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Delivery
    received_at_server: Mapped[datetime] = _ts()
    idempotency_key: Mapped[str] = mapped_column(String(100))
    client_entry_id: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(10), default="app", server_default="app")  # app | import
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("import_batches.id"))
    call_group: Mapped[str] = mapped_column(String(10))  # lead | dsa_cp | none
    # Calling state (derived)
    selection_status: Mapped[str | None] = mapped_column(String(60))  # "Allocate" or a "Not called – …" status
    selection_run_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(60), index=True)
    status_at: Mapped[datetime | None] = _ts()
    rag: Mapped[str] = mapped_column(String(10), default="PENDING", server_default="PENDING")
    rag_override: Mapped[str | None] = mapped_column(String(10))
    call_cycle: Mapped[int] = mapped_column(Integer, default=1, server_default="1")  # +1 after a number correction
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # in the current cycle
    first_caller_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    callback_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    priority_reason: Mapped[str | None] = mapped_column(String(60))
    last_called_on: Mapped[date | None] = mapped_column(Date)
    validated_on: Mapped[date | None] = mapped_column(Date)
    customer_validated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    first_validation: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    tcs_id: Mapped[str | None] = mapped_column(String(50), index=True)
    login_date: Mapped[date | None] = mapped_column(Date)
    login_source: Mapped[str | None] = mapped_column(String(10))  # register | manual
    lead_outcome: Mapped[str | None] = mapped_column(String(60))
    sankalp_success: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    so_action: Mapped[str | None] = mapped_column(String(40))
    so_action_date: Mapped[date | None] = mapped_column(Date)
    so_action_until: Mapped[date | None] = mapped_column(Date)  # None = open until login or rejection
    cc_action: Mapped[str | None] = mapped_column(String(40))
    cc_action_date: Mapped[date | None] = mapped_column(Date)
    expired_action: Mapped[str | None] = mapped_column(String(40))  # the last action whose window ran out unworked
    expired_on: Mapped[date | None] = mapped_column(Date)
    category_review: Mapped[str | None] = mapped_column(String(10))  # pending | done (branch answer code 2)
    created_at: Mapped[datetime] = _ts(server_default=func.now())
    updated_at: Mapped[datetime] = _ts(server_default=func.now(), onupdate=func.now())


class EntryEvent(Base):
    """Append-only history of an entry: made, selected, called, answered by the branch, corrected, logged in."""

    __tablename__ = "entry_events"
    id: Mapped[uuid.UUID] = _id()
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sankalp_entries.id"), index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detail: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _ts(server_default=func.now(), index=True)
