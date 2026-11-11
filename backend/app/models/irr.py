"""Weighted average IRR (BRD "Automation of Weighted Average IRR Calculation – HL & NHL (LAP)").

One row per disbursement (tranche) of the Disbursement Register, as uploaded by MIS. The calculation itself is in
app.services.irr; these tables only keep what was uploaded and what a user corrected.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Disbursement(Base):
    """A disbursement row of the register. Re-uploading the same row (same `dedup_key`) replaces it.

    Only rows that are neither `excluded` (status Cancelled / Reversed) nor an open `exception` (tenure or ROI missing,
    zero or negative) count in the IRR. Branch and region are the ones on the row at disbursement: the region comes
    from the branch master at upload time and is kept, so moving a branch later does not move old disbursements.
    """

    __tablename__ = "irr_disbursements"
    __table_args__ = (
        UniqueConstraint("company_id", "dedup_key", name="uq_irr_disbursement_key"),
        Index("ix_irr_disbursements_company_day", "company_id", "disbursement_date"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    # "R|<loan account>|<reference>", or "D|<loan account>|<date>|<amount>" when the row has no reference
    dedup_key: Mapped[str] = mapped_column(String(200))
    loan_account: Mapped[str] = mapped_column(String(50))
    disbursement_ref: Mapped[str | None] = mapped_column(String(50))
    disbursement_date: Mapped[date] = mapped_column(Date)
    product: Mapped[str] = mapped_column(String(100))  # as in the file
    product_key: Mapped[str] = mapped_column(String(100))  # lowercase, for the product mapping
    product_class: Mapped[str] = mapped_column(String(3))  # HL | NHL
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    tenure_months: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    roi: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))  # % a year, the "transaction IRR"
    status: Mapped[str | None] = mapped_column(String(50))
    excluded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    exception: Mapped[str | None] = mapped_column(String(200))  # why it is left out; None = usable
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_name: Mapped[str | None] = mapped_column(String(200))
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("import_batches.id"))
    source_row: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IrrSettings(Base):
    """Product mapping, reasonableness bands, financial-year start and display decimals. `data` is validated by
    app.services.irr.settings."""

    __tablename__ = "irr_settings"
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
