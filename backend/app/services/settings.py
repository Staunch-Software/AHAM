"""Company settings: the values of section 14 plus the open [Aham to decide] switches.

Every number in the business rules that the document calls a setting lives here, so changing a window or a target
never needs a code change. Defaults are the values in the document (version 1, 28 Oct 2026).
"""
import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompanySettings, SettingsHistory

DEFAULT_DESIGNATION_ROLES = {
    "RO": "sales_officer", "RM": "sales_officer", "ABM": "sales_officer", "SO": "sales_officer",
    "SALES OFFICER": "sales_officer",
    "BM": "branch_manager", "BRANCH MANAGER": "branch_manager",
    "RTM": "cluster_manager", "CLUSTER MANAGER": "cluster_manager",
    "RBH": "region_manager", "REGION MANAGER": "region_manager", "REGIONAL MANAGER": "region_manager",
    "PRODUCT MANAGER": "product_manager", "BUSINESS MANAGER": "business_manager",
}


class SankalpSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    takeoff_start: date = date(2026, 9, 22)
    first_call_date: date = date(2026, 9, 24)  # first entry date the call centre calls
    repeat_window_days: int = Field(30, ge=1, le=365)  # repeat entry / spoken-to window
    max_unanswered_lead: int = Field(9, ge=1, le=50)
    tries_per_day_lead: int = Field(2, ge=1, le=10)
    tries_per_day_dsa: int = Field(1, ge=1, le=10)
    max_slots_per_day: int = Field(3, ge=1, le=10)  # attempts that may be recorded per entry per day
    first_attempt_target_days: int = Field(1, ge=0, le=30)
    action_window_days: int = Field(14, ge=1, le=365)  # non-lead actions
    correct_number_window_days: int = Field(15, ge=1, le=365)
    amber_correction_window_days: int = Field(15, ge=1, le=365)
    branch_date_threshold_days: int = Field(14, ge=1, le=365)
    daily_entry_target: int = Field(10, ge=0, le=200)
    daily_lead_target: int = Field(5, ge=0, le=200)
    green_channel_construction_limit: int = Field(800_000, ge=0)  # self construction / improvement (₹)
    green_channel_purchase_limit: int = Field(1_500_000, ge=0)  # purchase / plot + construction (₹)
    present_codes: list[str] = ["P", "P(MS)", "P(R)", "P(MS)(R)"]
    designation_roles: dict[str, str] = DEFAULT_DESIGNATION_ROLES
    clock_skew_minutes: int = Field(5, ge=1, le=1440)  # device time this far ahead of the server is flagged
    # Daily selection run: "HH:MM" in the company time zone, or None to run it only from the call-centre portal.
    auto_selection_time: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    # ---- [Aham to decide] (defaults = today's behaviour) ----
    same_day_calling: bool = False  # 5.2: entries are called from the next day
    duplicate_tcs_rule: Literal["latest", "first"] = "latest"  # 11.1: which register row wins for a repeated TCS ID
    # 3 / 4.5: an SO with no attendance row that day is counted as present ("not marked") or as absent (AB)
    unmarked_attendance: Literal["present", "absent"] = "present"

    @model_validator(mode="after")
    def _check(self):
        self.designation_roles = {k.strip().upper(): v for k, v in self.designation_roles.items()}
        from app.security.rbac import ROLES
        bad = sorted({v for v in self.designation_roles.values() if v not in ROLES})
        if bad:
            raise ValueError(f"Unknown role(s) in designation_roles: {', '.join(bad)}")
        return self


async def load_settings(s: AsyncSession, company_id: uuid.UUID) -> SankalpSettings:
    row = await s.get(CompanySettings, company_id)
    return SankalpSettings.model_validate(row.data if row else {})


async def load_settings_on(s: AsyncSession, company_id: uuid.UUID, day: date) -> SankalpSettings:
    """The settings that applied on a past day (for reports such as daily compliance); today's if none were saved."""
    row = (await s.execute(select(SettingsHistory).where(
        SettingsHistory.company_id == company_id, SettingsHistory.effective_from <= day)
        .order_by(SettingsHistory.effective_from.desc()).limit(1))).scalar_one_or_none()
    return SankalpSettings.model_validate(row.data) if row else await load_settings(s, company_id)


async def save_settings(s: AsyncSession, company_id: uuid.UUID, values: SankalpSettings, actor_id: uuid.UUID,
                        today: date) -> None:
    """Saves the settings; they apply from today. Earlier days keep the values they had (settings_history)."""
    row = await s.get(CompanySettings, company_id)
    data = values.model_dump(mode="json")
    first = not (await s.execute(select(SettingsHistory.id).where(SettingsHistory.company_id == company_id).limit(1))).first()
    if first:  # the values in force before the first change, for every earlier day
        before = row.data if row else SankalpSettings().model_dump(mode="json")
        s.add(SettingsHistory(company_id=company_id, effective_from=date(2000, 1, 1), data=before))
    hist = (await s.execute(select(SettingsHistory).where(SettingsHistory.company_id == company_id,
                                                          SettingsHistory.effective_from == today))).scalar_one_or_none()
    if hist:
        hist.data, hist.saved_by = data, actor_id
    else:
        s.add(SettingsHistory(company_id=company_id, effective_from=today, data=data, saved_by=actor_id))
    if row is None:
        s.add(CompanySettings(company_id=company_id, data=data, updated_by=actor_id))
    else:
        row.data, row.updated_by = data, actor_id
