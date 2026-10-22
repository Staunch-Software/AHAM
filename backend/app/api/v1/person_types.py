import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_session
from app.models import Company, PersonType, SubmissionPersonType, User
from app.services.workflow import audit, ensure_company_defaults, load_person_types

router = APIRouter(prefix="/person-types", tags=["person-types"])


class PersonTypeIn(BaseModel):
    label: str = Field(min_length=1, max_length=100)


class PersonTypePatch(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    active: bool | None = None


class OrderIn(BaseModel):
    ids: list[uuid.UUID]


class SettingsPatch(BaseModel):
    required: bool | None = None
    allow_other: bool | None = None


async def _payload(s: AsyncSession, company_id: uuid.UUID) -> dict:
    company = await s.get(Company, company_id)
    types = await load_person_types(s, company_id)
    used = dict((await s.execute(
        select(SubmissionPersonType.person_type_id, func.count()).where(SubmissionPersonType.company_id == company_id,
                                                                      SubmissionPersonType.person_type_id.is_not(None))
        .group_by(SubmissionPersonType.person_type_id))).all())
    return {
        "items": [{"id": str(t.id), "label": t.label, "active": t.active, "sort_order": t.sort_order,
                   "times_used": used.get(t.id, 0)} for t in types],
        "settings": {"required": company.person_type_required, "allow_other": company.person_type_allow_other},
    }


async def _clash(s: AsyncSession, company_id: uuid.UUID, label: str, except_id: uuid.UUID | None = None) -> bool:
    q = select(PersonType.id).where(PersonType.company_id == company_id, PersonType.active,
                                    func.lower(PersonType.label) == label.strip().lower())
    if except_id:
        q = q.where(PersonType.id != except_id)
    return (await s.execute(q.limit(1))).first() is not None


async def _commit(s: AsyncSession) -> None:
    try:
        await s.commit()
    except IntegrityError:
        await s.rollback()
        raise HTTPException(409, "An active option with this name already exists")


async def _own(s: AsyncSession, admin: User, type_id: uuid.UUID) -> PersonType:
    t = await s.get(PersonType, type_id)
    if not t or t.company_id != admin.company_id:
        raise HTTPException(404, "Not found")  # other companies' options are invisible
    return t


@router.get("")
async def list_types(admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    await ensure_company_defaults(s, admin.company_id)  # first visit seeds the starter list, never edits existing
    await s.commit()
    return await _payload(s, admin.company_id)


@router.post("", status_code=201)
async def add_type(body: PersonTypeIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    label = body.label.strip()
    if not label:
        raise HTTPException(422, "Name is required")
    if await _clash(s, admin.company_id, label):
        raise HTTPException(409, "An active option with this name already exists")
    top = (await s.execute(select(func.coalesce(func.max(PersonType.sort_order), -1)).where(PersonType.company_id == admin.company_id))).scalar_one()
    t = PersonType(company_id=admin.company_id, label=label, sort_order=top + 1)
    s.add(t)
    await s.flush()
    audit(s, admin, "person_type.create", "person_type", t.id)
    await _commit(s)
    return await _payload(s, admin.company_id)


@router.patch("/settings")
async def update_settings(body: SettingsPatch, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    company = await s.get(Company, admin.company_id)
    if body.required is not None:
        company.person_type_required = body.required
    if body.allow_other is not None:
        company.person_type_allow_other = body.allow_other
    audit(s, admin, "person_type.settings", "company", company.id)
    await s.commit()
    return await _payload(s, admin.company_id)


@router.put("/order")
async def reorder(body: OrderIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    types = {t.id: t for t in await load_person_types(s, admin.company_id)}
    if len(set(body.ids)) != len(body.ids) or not set(body.ids) <= set(types):
        raise HTTPException(422, "Unknown or repeated option id")
    for pos, tid in enumerate(body.ids):
        types[tid].sort_order = pos
    # options not mentioned keep their relative order after the listed ones
    rest = sorted((t for tid, t in types.items() if tid not in set(body.ids)), key=lambda t: (t.sort_order, t.label))
    for i, t in enumerate(rest, start=len(body.ids)):
        t.sort_order = i
    audit(s, admin, "person_type.reorder", "company", admin.company_id)
    await s.commit()
    return await _payload(s, admin.company_id)


@router.patch("/{type_id}")
async def update_type(type_id: uuid.UUID, body: PersonTypePatch, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    t = await _own(s, admin, type_id)
    new_label = body.label.strip() if body.label is not None else t.label
    new_active = t.active if body.active is None else body.active
    if not new_label:
        raise HTTPException(422, "Name is required")
    if new_active and await _clash(s, admin.company_id, new_label, except_id=t.id):
        raise HTTPException(409, "An active option with this name already exists")
    t.label, t.active = new_label, new_active  # history keeps the id; old reports keep the label they were saved with
    audit(s, admin, "person_type.update", "person_type", t.id)
    await _commit(s)
    return await _payload(s, admin.company_id)
