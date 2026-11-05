"""Call centre and branch hand-off (sections 5-13): allocation, attempts, lead card, branch answers, tracker, logins."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


_ts = lambda **kw: mapped_column(DateTime(timezone=True), **kw)  # noqa: E731


class CallerDay(Base):
    """The caller of the day for a branch (section 6): new entries of that branch go to this caller."""

    __tablename__ = "caller_days"
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    caller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    set_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    set_at: Mapped[datetime] = _ts(server_default=func.now())


class SelectionRun(Base):
    """One run of the daily selection (section 5) and allocation (section 6) for a run date."""

    __tablename__ = "selection_runs"
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    run_date: Mapped[date] = mapped_column(Date)
    started_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # None = the automatic run
    started_at: Mapped[datetime] = _ts(server_default=func.now())
    counts: Mapped[dict | None] = mapped_column(JSONB)


class CallAllocation(Base):
    """An entry on a caller's list. kind: fresh | retry | priority | followup. status: open | done | unreturned.

    caller_id is empty when the entry's branch had no caller of the day: the master owner assigns it."""

    __tablename__ = "call_allocations"
    __table_args__ = (Index("ix_alloc_open", "company_id", "caller_id", "status"),)
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sankalp_entries.id"), index=True)
    caller_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    run_date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(12), default="open")
    created_at: Mapped[datetime] = _ts(server_default=func.now())
    closed_at: Mapped[datetime | None] = _ts()


class CallAttempt(Base):
    """One try (section 7): time slot + outcome, the answers when connected, and the row status it produced."""

    __tablename__ = "call_attempts"
    __table_args__ = (Index("ix_attempt_entry_date", "entry_id", "call_date"),)
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sankalp_entries.id"))
    caller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    call_date: Mapped[date] = mapped_column(Date)
    slot: Mapped[str] = mapped_column(String(5))  # "09-10" ... "06-07"
    outcome: Mapped[str] = mapped_column(String(30))
    cycle: Mapped[int] = mapped_column(Integer, default=1)
    next_date: Mapped[date | None] = mapped_column(Date)  # callback requested / next step date
    answers: Mapped[dict | None] = mapped_column(JSONB)  # questions of 7.2 / 7.3 when connected
    row_status: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = _ts(server_default=func.now())


class LeadCard(Base):
    """Section 7.4. Filled while on the call once Loan need shows a loan type. The lead ID never closes a lead."""

    __tablename__ = "lead_cards"
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sankalp_entries.id"), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    handling_branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    loan_requirement: Mapped[int | None] = mapped_column(Integer)  # rupees
    lead_id: Mapped[str | None] = mapped_column(String(50), index=True)  # TCS lead ID
    lead_id_at: Mapped[datetime | None] = _ts()
    data: Mapped[dict] = mapped_column(JSONB, default=dict)  # the other card fields
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_at: Mapped[datetime] = _ts(server_default=func.now(), onupdate=func.now())


class BranchAnswer(Base):
    """Section 12.4: one code and one date per lead, given by the BM (or the RBH for a branch without a BM).

    green_channel: pending | upheld | overruled when an R2/R3 reject hits a green-channel lead (head-office check)."""

    __tablename__ = "branch_answers"
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sankalp_entries.id"), index=True)
    code: Mapped[str] = mapped_column(String(4))
    answer_date: Mapped[date | None] = mapped_column(Date)  # the login / follow-up / visit date asked for
    responded_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    green_channel: Mapped[str | None] = mapped_column(String(10))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = _ts()
    created_at: Mapped[datetime] = _ts(server_default=func.now())


class FollowupTracker(Base):
    """Section 13.3: the master owner's manual follow-up row, one per entry."""

    __tablename__ = "followup_tracker"
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sankalp_entries.id"), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    owner: Mapped[str | None] = mapped_column(String(12))  # branch | call_centre | done
    action_type: Mapped[str | None] = mapped_column(String(60))
    caller_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    followup_date: Mapped[date | None] = mapped_column(Date)
    outcome: Mapped[str | None] = mapped_column(String(40))
    tcs_id: Mapped[str | None] = mapped_column(String(50))
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    rag_override: Mapped[str | None] = mapped_column(String(10))
    immediate_callback: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_at: Mapped[datetime] = _ts(server_default=func.now(), onupdate=func.now())


class LoginRegisterRow(Base):
    """One row of the MIS login register (section 11). `phones` holds every valid number of the contact cell."""

    __tablename__ = "login_register_rows"
    __table_args__ = (
        Index("ix_register_tcs", "company_id", "tcs_id"),
        Index("ix_register_phones", "phones", postgresql_using="gin"),
    )
    id: Mapped[uuid.UUID] = _id()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batches.id"), index=True)
    row_no: Mapped[int] = mapped_column(Integer)
    tcs_id: Mapped[str] = mapped_column(String(50))
    contacts_raw: Mapped[str | None] = mapped_column(String(300))
    phones: Mapped[list] = mapped_column(JSONB, default=list)
    login_date: Mapped[date | None] = mapped_column(Date)
    product: Mapped[str | None] = mapped_column(String(100))
    final_status: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(100))
    emp_code: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = _ts(server_default=func.now())
