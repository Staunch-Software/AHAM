import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

_ts = lambda **kw: mapped_column(DateTime(timezone=True), **kw)


class EntryDocument(Base):
    """An attached document or scanned certificate for a Sankalp entry (KYC, income, property, etc.)."""

    __tablename__ = "entry_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sankalp_entries.id"), index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(50))  # kyc, income, property, application, other
    sub_type: Mapped[str | None] = mapped_column(String(100))  # aadhaar, pan, payslip, sale_deed, etc.
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts(server_default=func.now())
