"""Shared helpers for managed option lists, report references and the dynamic-option overlay."""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Company, CompanyCounter, PersonType, ReviewReason, User
from app.services.form_schema import overlay_dynamic_options

DEFAULT_PERSON_TYPES = ["Customer", "Dealer", "Distributor", "Supplier", "Business Partner"]
# (code, label, pre-filled message, comment required)
DEFAULT_REASONS = [
    ("missing_information", "Missing information", "Complete the required meeting description.", False),
    ("unclear_photo", "Unclear photo", "Upload a clearer photo of the relevant evidence.", False),
    ("incorrect_details", "Incorrect details", "Verify the submitted contact information.", False),
    ("incomplete_meeting", "Incomplete meeting", "Fill in the missing meeting details.", False),
    ("evidence_required", "Evidence required", "Attach the required supporting photo.", False),
    ("other", "Other", None, True),
]


async def ensure_company_defaults(s: AsyncSession, company_id: uuid.UUID) -> None:
    """Adds the starter person types and rejection reasons if the company has none. Never touches existing ones."""
    if not (await s.execute(select(PersonType.id).where(PersonType.company_id == company_id).limit(1))).first():
        for i, label in enumerate(DEFAULT_PERSON_TYPES):
            s.add(PersonType(company_id=company_id, label=label, sort_order=i))
    if not (await s.execute(select(ReviewReason.id).where(ReviewReason.company_id == company_id).limit(1))).first():
        for i, (code, label, msg, needs) in enumerate(DEFAULT_REASONS):
            s.add(ReviewReason(company_id=company_id, code=code, label=label, default_message=msg,
                               requires_comment=needs, sort_order=i))
    await s.flush()


async def next_reference(s: AsyncSession, company_id: uuid.UUID, when: datetime) -> str:
    """FS-<year>-<n>, numbered per company and year. The upsert is atomic: concurrent reports never share a number."""
    key = f"ref_{when:%Y}"
    stmt = pg_insert(CompanyCounter).values(company_id=company_id, key=key, value=1)
    stmt = stmt.on_conflict_do_update(index_elements=["company_id", "key"], set_={"value": CompanyCounter.value + 1})
    n = (await s.execute(stmt.returning(CompanyCounter.value))).scalar_one()
    return f"FS-{when:%Y}-{n:04d}"


async def load_person_types(s: AsyncSession, company_id: uuid.UUID) -> list[PersonType]:
    rows = await s.execute(
        select(PersonType).where(PersonType.company_id == company_id).order_by(PersonType.sort_order, PersonType.label)
    )
    return list(rows.scalars().all())


async def overlay_for_company(s: AsyncSession, company_id: uuid.UUID, schema: dict, *, delivery: bool) -> dict:
    """Injects the company's current person types. delivery=True lists only ACTIVE options (what an agent may pick
    now); delivery=False accepts every existing id, so a report made offline with a since-retired option is still valid."""
    company = await s.get(Company, company_id)
    types = await load_person_types(s, company_id)
    opts = [{"value": str(t.id), "label": t.label} for t in types if (t.active or not delivery)]
    return overlay_dynamic_options(
        schema, {"person_types": opts},
        required=company.person_type_required, allow_other=company.person_type_allow_other,
    )


def audit(s: AsyncSession, actor: User, action: str, entity: str, entity_id) -> None:
    s.add(AuditLog(company_id=actor.company_id, actor_id=actor.id, action=action, entity_type=entity, entity_id=str(entity_id)))
