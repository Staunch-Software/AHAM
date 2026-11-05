"""Reference data the Sankalp flow needs besides the roster: CP sub-types, settings, holidays, attendance, imports."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class CpSubtype(Base):
    """An option of the "CP sub-type" list (asked only when Category = Contact Point). The id is the stable key
    stored on entries; the label can change and entries keep the label they were saved with."""

    __tablename__ = "cp_subtypes"
    __table_args__ = (
        # No two ACTIVE options may share a name (case-insensitive); retired ones may be reused.
        Index("uq_cp_subtypes_active_label", "company_id", func.lower(text("label")), unique=True,
              postgresql_where=text("active")),
    )
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    label: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CompanySettings(Base):
    """Section 14 values and the open [Aham to decide] switches. `data` is validated by app.services.settings."""

    __tablename__ = "company_settings"
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SettingsHistory(Base):
    """Every saved version of the settings with the day it applies from, so a report for a past day (daily
    compliance) uses the targets that applied then."""

    __tablename__ = "settings_history"
    __table_args__ = (UniqueConstraint("company_id", "effective_from", name="uq_settings_history_day"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    effective_from: Mapped[date] = mapped_column(Date)
    data: Mapped[dict] = mapped_column(JSONB)
    saved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Holiday(Base):
    """For the count-date rule: an entry made on a holiday counts on the next working day."""

    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("company_id", "day"),)
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(100))


class Attendance(Base):
    """Daily attendance status code per employee (from the attendance upload)."""

    __tablename__ = "attendance"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(20))


class ImportBatch(Base):
    """One uploaded file (roster, attendance, login register): who, when, and what happened to each row."""

    __tablename__ = "import_batches"
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str | None] = mapped_column(String(255))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_ok: Mapped[int] = mapped_column(Integer, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict | None] = mapped_column(JSONB)
    errors: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
