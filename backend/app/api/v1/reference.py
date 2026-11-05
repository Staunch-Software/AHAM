"""Settings (section 14), holidays, and the CP sub-type list."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_perm
from app.core.db import get_session
from app.models import CpSubtype, Holiday, SankalpEntry, User
from app.services.reference import audit, ensure_company_defaults, load_cp_subtypes, recount_days_near
from app.services.sankalp.ops import company_today
from app.services.settings import SankalpSettings, load_settings, save_settings

router = APIRouter(tags=["reference"])


# ---- Settings ----
@router.get("/settings")
async def get_settings_(user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return (await load_settings(s, user.company_id)).model_dump(mode="json")


@router.patch("/settings")
async def patch_settings(body: dict, admin: User = Depends(require_perm("settings.manage")),
                         s: AsyncSession = Depends(get_session)):
    current = (await load_settings(s, admin.company_id)).model_dump(mode="json")
    unknown = sorted(set(body) - set(current))
    if unknown:
        raise HTTPException(422, f"Unknown setting(s): {', '.join(unknown)}")
    try:
        merged = SankalpSettings.model_validate({**current, **body})
    except ValidationError as e:
        raise HTTPException(422, [{"field": ".".join(map(str, er["loc"])), "message": er["msg"]} for er in e.errors()])
    new = merged.model_dump(mode="json")
    changes = {k: {"old": current[k], "new": new[k]} for k in new if new[k] != current.get(k)}
    await save_settings(s, admin.company_id, merged, admin.id, await company_today(s, admin.company_id))
    audit(s, admin, "settings.update", "company", admin.company_id, details=changes)
    await s.commit()
    return new


# ---- Holidays ----
class HolidayIn(BaseModel):
    day: date
    name: str = Field(min_length=1, max_length=100)


@router.get("/holidays")
async def list_holidays(year: int | None = None, user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    q = select(Holiday).where(Holiday.company_id == user.company_id).order_by(Holiday.day)
    if year:
        q = q.where(Holiday.day >= date(year, 1, 1), Holiday.day <= date(year, 12, 31))
    return [{"id": str(h.id), "day": h.day, "name": h.name} for h in (await s.execute(q)).scalars().all()]


@router.post("/holidays", status_code=201)
async def add_holiday(body: HolidayIn, user: User = Depends(require_perm("reference.import")),
                      s: AsyncSession = Depends(get_session)):
    h = Holiday(company_id=user.company_id, day=body.day, name=body.name.strip())
    s.add(h)
    try:
        await s.flush()
    except IntegrityError:
        await s.rollback()
        raise HTTPException(409, "That day is already a holiday")
    # 4.4: an entry made on a day that is now a holiday counts on the next working day
    moved = await recount_days_near(s, user.company_id, h.day)
    audit(s, user, "holiday.create", "holiday", h.id, details={"day": str(h.day), "name": h.name, "entries_moved": moved})
    await s.commit()
    return {"id": str(h.id), "day": h.day, "name": h.name, "entries_moved": moved}


@router.delete("/holidays/{holiday_id}", status_code=204)
async def delete_holiday(holiday_id: uuid.UUID, user: User = Depends(require_perm("reference.import")),
                         s: AsyncSession = Depends(get_session)):
    """Entries made on that day (or on the Sundays just before it) count on it again."""
    h = await s.get(Holiday, holiday_id)
    if not h or h.company_id != user.company_id:
        raise HTTPException(404, "Not found")
    day, name = h.day, h.name
    await s.delete(h)
    await s.flush()
    moved = await recount_days_near(s, user.company_id, day)
    audit(s, user, "holiday.delete", "holiday", holiday_id, details={"day": str(day), "name": name, "entries_moved": moved})
    await s.commit()


# ---- CP sub-types (asked only when Category = Contact Point) ----
class SubtypeIn(BaseModel):
    label: str = Field(min_length=1, max_length=100)


class SubtypePatch(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    active: bool | None = None


class OrderIn(BaseModel):
    ids: list[uuid.UUID]


require_lists = require_perm("cp_subtypes.manage")


async def _payload(s: AsyncSession, company_id: uuid.UUID) -> dict:
    types = await load_cp_subtypes(s, company_id)
    used = dict((await s.execute(
        select(SankalpEntry.cp_subtype_id, func.count()).where(SankalpEntry.company_id == company_id,
                                                               SankalpEntry.cp_subtype_id.is_not(None))
        .group_by(SankalpEntry.cp_subtype_id))).all())
    return {"items": [{"id": str(t.id), "label": t.label, "active": t.active, "sort_order": t.sort_order,
                       "times_used": used.get(t.id, 0)} for t in types]}


async def _clash(s: AsyncSession, company_id: uuid.UUID, label: str, except_id: uuid.UUID | None = None) -> bool:
    q = select(CpSubtype.id).where(CpSubtype.company_id == company_id, CpSubtype.active,
                                   func.lower(CpSubtype.label) == label.strip().lower())
    if except_id:
        q = q.where(CpSubtype.id != except_id)
    return (await s.execute(q.limit(1))).first() is not None


async def _commit(s: AsyncSession) -> None:
    try:
        await s.commit()
    except IntegrityError:
        await s.rollback()
        raise HTTPException(409, "An active option with this name already exists")


async def _own(s: AsyncSession, user: User, type_id: uuid.UUID) -> CpSubtype:
    t = await s.get(CpSubtype, type_id)
    if not t or t.company_id != user.company_id:
        raise HTTPException(404, "Not found")
    return t


@router.get("/cp-subtypes/active")
async def active_subtypes(user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    """What a Sales Officer may pick now (the app caches it for offline use)."""
    await ensure_company_defaults(s, user.company_id)
    await s.commit()
    return [{"id": str(t.id), "label": t.label} for t in await load_cp_subtypes(s, user.company_id) if t.active]


@router.get("/cp-subtypes")
async def list_subtypes(admin: User = Depends(require_lists), s: AsyncSession = Depends(get_session)):
    await ensure_company_defaults(s, admin.company_id)
    await s.commit()
    return await _payload(s, admin.company_id)


@router.post("/cp-subtypes", status_code=201)
async def add_subtype(body: SubtypeIn, admin: User = Depends(require_lists), s: AsyncSession = Depends(get_session)):
    label = body.label.strip()
    if not label:
        raise HTTPException(422, "Name is required")
    if await _clash(s, admin.company_id, label):
        raise HTTPException(409, "An active option with this name already exists")
    top = (await s.execute(select(func.coalesce(func.max(CpSubtype.sort_order), -1))
                           .where(CpSubtype.company_id == admin.company_id))).scalar_one()
    t = CpSubtype(company_id=admin.company_id, label=label, sort_order=top + 1)
    s.add(t)
    await s.flush()
    audit(s, admin, "cp_subtype.create", "cp_subtype", t.id)
    await _commit(s)
    return await _payload(s, admin.company_id)


@router.put("/cp-subtypes/order")
async def reorder(body: OrderIn, admin: User = Depends(require_lists), s: AsyncSession = Depends(get_session)):
    types = {t.id: t for t in await load_cp_subtypes(s, admin.company_id)}
    if len(set(body.ids)) != len(body.ids) or not set(body.ids) <= set(types):
        raise HTTPException(422, "Unknown or repeated option id")
    for pos, tid in enumerate(body.ids):
        types[tid].sort_order = pos
    rest = sorted((t for tid, t in types.items() if tid not in set(body.ids)), key=lambda t: (t.sort_order, t.label))
    for i, t in enumerate(rest, start=len(body.ids)):
        t.sort_order = i
    audit(s, admin, "cp_subtype.reorder", "company", admin.company_id)
    await s.commit()
    return await _payload(s, admin.company_id)


@router.patch("/cp-subtypes/{type_id}")
async def update_subtype(type_id: uuid.UUID, body: SubtypePatch, admin: User = Depends(require_lists),
                         s: AsyncSession = Depends(get_session)):
    t = await _own(s, admin, type_id)
    new_label = body.label.strip() if body.label is not None else t.label
    new_active = t.active if body.active is None else body.active
    if not new_label:
        raise HTTPException(422, "Name is required")
    if new_active and await _clash(s, admin.company_id, new_label, except_id=t.id):
        raise HTTPException(409, "An active option with this name already exists")
    t.label, t.active = new_label, new_active  # entries keep the label they were saved with
    audit(s, admin, "cp_subtype.update", "cp_subtype", t.id)
    await _commit(s)
    return await _payload(s, admin.company_id)
