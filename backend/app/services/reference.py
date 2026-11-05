"""Shared helpers: audit log, company defaults (CP sub-types), holidays."""
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, CpSubtype, Holiday, SankalpEntry, User

# Examples given in the business logic (section 4.1); admins add the rest of the list in the HR & Admin portal.
DEFAULT_CP_SUBTYPES = ["Sand / Gravel / Brick Shop", "Other Hardware Shop", "Other"]


def audit(s: AsyncSession, actor: User, action: str, entity: str, entity_id, details: dict | None = None) -> None:
    s.add(AuditLog(company_id=actor.company_id, actor_id=actor.id, action=action, entity_type=entity,
                   entity_id=str(entity_id), details=details or None))


async def ensure_company_defaults(s: AsyncSession, company_id: uuid.UUID) -> None:
    """Adds the starter CP sub-types if the company has none. Never touches existing ones."""
    if not (await s.execute(select(CpSubtype.id).where(CpSubtype.company_id == company_id).limit(1))).first():
        for i, label in enumerate(DEFAULT_CP_SUBTYPES):
            s.add(CpSubtype(company_id=company_id, label=label, sort_order=i))
    await s.flush()


async def load_cp_subtypes(s: AsyncSession, company_id: uuid.UUID) -> list[CpSubtype]:
    rows = await s.execute(
        select(CpSubtype).where(CpSubtype.company_id == company_id).order_by(CpSubtype.sort_order, CpSubtype.label)
    )
    return list(rows.scalars().all())


async def holiday_set(s: AsyncSession, company_id: uuid.UUID, start: date | None = None) -> set[date]:
    q = select(Holiday.day).where(Holiday.company_id == company_id)
    if start:
        q = q.where(Holiday.day >= start)
    return set((await s.execute(q)).scalars().all())


async def recount_days_near(s: AsyncSession, company_id: uuid.UUID, day: date) -> int:
    """4.4 after a holiday is added or removed: entries made on that day, or on the Sundays / holidays just before it,
    get their count date worked out again. The Entry ID and the entry date never change."""
    from app.services import calendar

    holidays = await holiday_set(s, company_id, day - timedelta(days=30))
    rows = (await s.execute(select(SankalpEntry).where(
        SankalpEntry.company_id == company_id, SankalpEntry.entry_date >= day - timedelta(days=14),
        SankalpEntry.entry_date <= day))).scalars().all()
    changed = 0
    for e in rows:
        new = calendar.count_date(e.entry_date, holidays)
        if new != e.count_date:
            e.count_date, changed = new, changed + 1
    return changed
