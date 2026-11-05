"""What a caller records (section 7): the attempt, the questions once connected, and the lead card."""
import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.sankalp import rules as R

Opt = lambda values: Literal[tuple(values)] | None  # noqa: E731 - an optional choice from a fixed list


class Answers(BaseModel):
    """7.2 (Lead questions) and 7.3 (DSA/CP questions). Every answer may be left blank: classification handles that
    (a blank Loan need gives "Amber – answers missing")."""

    model_config = ConfigDict(extra="forbid")
    # 7.3 DSA/CP
    dsa_rag: Opt(R.DSA_RAG) = None  # type: ignore[valid-type]
    needs_home_loan: Opt(["Yes", "No"]) = None  # type: ignore[valid-type]
    # 7.2 Lead
    name_check: Opt(R.NAME_CHECK) = None  # type: ignore[valid-type]
    name_given: str | None = Field(None, max_length=200)
    visit: Opt(R.VISIT) = None  # type: ignore[valid-type]
    relationship: Opt(R.RELATIONSHIP) = None  # type: ignore[valid-type]
    loan_need: Opt(R.LOAN_NEED) = None  # type: ignore[valid-type]
    timeline: Opt(R.TIMELINE) = None  # type: ignore[valid-type]
    income: Opt(R.INCOME) = None  # type: ignore[valid-type]
    documents: Opt(R.DOCUMENTS) = None  # type: ignore[valid-type]
    next_step: Opt(R.NEXT_STEP) = None  # type: ignore[valid-type]
    next_date: date | None = None
    purpose: Opt(R.PURPOSE) = None  # type: ignore[valid-type]
    own_contribution: Opt(R.OWN_CONTRIBUTION) = None  # type: ignore[valid-type]
    remarks: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def _dates(self):
        if self.next_date and self.next_date.weekday() == 6:
            raise ValueError("Next date must be a working day (not a Sunday)")
        return self


class AttemptIn(BaseModel):
    slot: Literal[tuple(R.SLOTS)]  # type: ignore[valid-type]
    outcome: Literal[tuple(R.OUTCOMES)]  # type: ignore[valid-type]
    next_date: date | None = None  # when the customer asked to be called back
    answers: Answers | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.outcome == R.CALLBACK and not self.next_date:
            raise ValueError("Pick the date the customer asked to be called back")
        if self.next_date and self.next_date.weekday() == 6:
            raise ValueError("Callback date must be a working day (not a Sunday)")
        if self.answers is not None and self.outcome != R.CONNECTED:
            raise ValueError("Questions are answered only on a connected call")
        return self


class LeadCardIn(BaseModel):
    """7.4. Opened once Loan need shows a loan type; filled while the caller is on the call."""

    model_config = ConfigDict(extra="forbid")
    handling_branch_id: uuid.UUID | None = None  # blank = the SO's branch
    age: int | None = Field(None, ge=18, le=100)
    date_of_birth: date | None = None
    address: str | None = Field(None, max_length=300)
    city: str | None = Field(None, max_length=100)
    property_pincode: str | None = Field(None, pattern=r"^\d{6}$")
    business_pincode: str | None = Field(None, pattern=r"^\d{6}$")
    payslip_or_itr: bool | None = None
    job_profile: str | None = Field(None, max_length=100)
    individual_monthly_income: int | None = Field(None, ge=0, le=100_000_000)
    family_monthly_income: int | None = Field(None, ge=0, le=100_000_000)
    vehicle: bool | None = None
    vehicle_type: str | None = Field(None, max_length=50)
    cibil_score: int | None = Field(None, ge=300, le=900)  # blank if the customer does not know it
    bounce_last_6_months: bool | None = None
    property_owner: str | None = Field(None, max_length=100)
    property_area: str | None = Field(None, max_length=100)
    approved_property: str | None = Field(None, max_length=50)
    property_type: str | None = Field(None, max_length=50)
    loan_purpose: str | None = Field(None, max_length=200)
    loan_requirement: int | None = Field(None, ge=1, le=1_000_000_000)  # rupees: always a number
    lead_id: str | None = Field(None, max_length=50)  # the TCS lead ID, entered only when the lead is generated

    @model_validator(mode="after")
    def _check(self):
        if self.lead_id is not None:
            self.lead_id = self.lead_id.strip() or None
        if self.lead_id and not self.loan_requirement:
            raise ValueError("Loan requirement (₹) is compulsory once a lead ID is entered")
        return self


class BranchAnswerIn(BaseModel):
    code: Literal[tuple(R.BRANCH_CODES)]  # type: ignore[valid-type]
    answer_date: date | None = None  # the login / follow-up / visit date the code asks for
    note: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _check(self):
        asked = R.BRANCH_CODES[self.code][1]
        if asked and not self.answer_date:
            raise ValueError(f"Code {self.code} needs the {asked.lower()}")
        if not asked:
            self.answer_date = None
        return self


class TrackerIn(BaseModel):
    """13.3: the master owner's manual follow-up row (one per entry)."""

    model_config = ConfigDict(extra="forbid")
    owner: Literal[tuple(R.TRACKER_OWNERS)] | None = None  # type: ignore[valid-type]
    action_type: str | None = Field(None, max_length=60)
    caller_id: uuid.UUID | None = None
    followup_date: date | None = None
    outcome: Literal[tuple(R.TRACKER_OUTCOMES)] | None = None  # type: ignore[valid-type]
    tcs_id: str | None = Field(None, max_length=50)
    reject_reason: str | None = Field(None, max_length=200)
    rag_override: Literal[tuple(R.RAGS[1:])] | None = None  # type: ignore[valid-type]
    immediate_callback: bool = False
    notes: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _outcome_needs(self):
        if self.outcome == "Logged in" and not (self.tcs_id or "").strip():
            raise ValueError("Type the TCS ID: a login counts only with its TCS ID (11.1)")
        if self.outcome == "Rejected" and not (self.reject_reason or "").strip():
            raise ValueError("Give the reject reason")
        return self
