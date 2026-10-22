import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FormDefinition(Base):
    __tablename__ = "form_definitions"
    __table_args__ = (UniqueConstraint("company_id", "key"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    key: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FormVersion(Base):
    """Immutable once inserted. `schema` is validated by app.services.form_schema before insert.

    status: published (accepted) | deprecated (still accepted from old offline drafts) | retired (rejected).
    """

    __tablename__ = "form_versions"
    __table_args__ = (UniqueConstraint("form_id", "version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_definitions.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    schema: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="published")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FormAssignment(Base):
    """branch_id NULL = form available to every branch of the company."""

    __tablename__ = "form_assignments"
    __table_args__ = (UniqueConstraint("form_id", "branch_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_definitions.id"), index=True)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
