"""Managed option lists, review history, photo links across revisions, and reporting targets."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class PersonType(Base):
    """An option of the 'Type of person' dropdown. The id is the stable key stored in reports; labels can change."""

    __tablename__ = "person_types"
    __table_args__ = (
        # No two ACTIVE options may share a name (case-insensitive); retired ones may be reused.
        Index("uq_person_types_active_label", "company_id", func.lower(text("label")), unique=True,
              postgresql_where=text("active")),
    )
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    label: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReviewReason(Base):
    """Selectable rejection reasons (configurable per company). `default_message` pre-fills the reviewer's comment."""

    __tablename__ = "review_reasons"
    __table_args__ = (UniqueConstraint("company_id", "code"),)
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(100))
    default_message: Mapped[str | None] = mapped_column(String(500))
    requires_comment: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class SubmissionReview(Base):
    """Append-only review history. decision: approved | rejected | reopened."""

    __tablename__ = "submission_reviews"
    id: Mapped[uuid.UUID] = _id()
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_submissions.id"), index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(20))
    reason_code: Mapped[str | None] = mapped_column(String(50))
    reason_label: Mapped[str | None] = mapped_column(String(100))  # snapshot, survives later renames
    comment: Mapped[str | None] = mapped_column(Text)
    flags: Mapped[list | None] = mapped_column(JSONB)  # [{path, note}] pointing at meetings / photos
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class SubmissionPhotoLink(Base):
    """Which photos belong to which report revision. A corrected revision can keep photos from the earlier one."""

    __tablename__ = "submission_photo_links"
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_submissions.id"), primary_key=True)
    photo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submission_photos.id"), primary_key=True, index=True)
    group_key: Mapped[str | None] = mapped_column(String(100))
    field_key: Mapped[str | None] = mapped_column(String(100))


class SubmissionPersonType(Base):
    """One row per meeting entry that chose a managed 'type of person' option: used for filters and analytics."""

    __tablename__ = "submission_person_types"
    __table_args__ = (Index("ix_spt_company_type", "company_id", "person_type_id"),)
    id: Mapped[uuid.UUID] = _id()
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_submissions.id"), index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    entry_path: Mapped[str] = mapped_column(String(100))
    person_type_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("person_types.id"))
    other_text: Mapped[str | None] = mapped_column(String(100))
    label_snapshot: Mapped[str] = mapped_column(String(100))


class ReportTarget(Base):
    """Optional expected number of reports per week or month for a branch or an agent."""

    __tablename__ = "report_targets"
    __table_args__ = (
        UniqueConstraint("company_id", "branch_id", "period", name="uq_target_branch_period"),
        UniqueConstraint("company_id", "user_id", "period", name="uq_target_user_period"),
    )
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    scope: Mapped[str] = mapped_column(String(10))  # branch | agent
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    period: Mapped[str] = mapped_column(String(10))  # weekly | monthly
    target: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CompanyCounter(Base):
    """Atomic per-company counters (report references FS-<year>-<n>)."""

    __tablename__ = "company_counters"
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
