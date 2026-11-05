"""Sankalp entries (section 4): made by Sales Officers in the app, seen by everyone above them in their scope."""
import hashlib
import json
import re
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.db import SessionLocal, get_session
from app.models import Branch, Company, CpSubtype, EntryEvent, Holiday, OutboxEvent, Photo, Region, SankalpEntry, User
from app.services import calendar
from app.services.geocoding import place_status_for_api
from app.services.periods import tz_of
from app.services.phone import clean_phone, is_valid_phone
from app.services.reference import holiday_set
from app.services.sankalp import rules
from app.services.sankalp.ops import company_today
from app.services.sankalp.views import calling_detail
from app.services.scope import entry_scope
from app.services.settings import load_settings
from app.services.tabular import parse_date
from app.storage.base import sign_file_url
from app.workers.outbox import notify_outbox

router = APIRouter(tags=["entries"])
LocationStatus = Literal["obtained", "permission_denied", "services_disabled", "timeout", "unavailable"]
MAX_PHOTOS = 5


class EntryLocation(BaseModel):
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    accuracy_m: float | None = Field(None, ge=0, le=100000)
    fix_at_device: datetime | None = None
    status: LocationStatus = "unavailable"


class EntryIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    client_entry_id: str = Field(min_length=1, max_length=100)
    category: Literal[tuple(rules.CATEGORIES)]  # type: ignore[valid-type]
    cp_subtype_id: uuid.UUID | None = None
    person_name: str = Field(max_length=200)
    phone: str = Field(max_length=50)
    description: str = Field(max_length=2000)
    keka_photo_time: time | None = None
    photo_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_PHOTOS)
    # The moment Submit was pressed on the phone. An entry made offline keeps this time when it syncs later.
    submitted_at_device: datetime
    device_tz_offset_min: int | None = Field(None, ge=-840, le=840)
    # The phone's own clock reading when it last heard from the server. A Submit time earlier than that means the
    # clock was set back since (e.g. to put today's meeting on yesterday): flagged "check the time".
    device_clock_at_last_contact: datetime | None = None
    location: EntryLocation = EntryLocation()

    @field_validator("submitted_at_device", "device_clock_at_last_contact")
    @classmethod
    def _aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("must include a time zone offset")
        return v


def _f(v):
    return None if v is None else float(v)


def _canon_hash(body: EntryIn) -> str:
    raw = json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _receipt(e: SankalpEntry, duplicate: bool) -> dict:
    return {"id": str(e.id), "entry_code": e.entry_code, "client_entry_id": e.client_entry_id,
            "received_at_server": e.received_at_server, "entry_date": e.entry_date, "count_date": e.count_date,
            "duplicate": duplicate}


async def _existing(s: AsyncSession, company_id: uuid.UUID, key: str) -> SankalpEntry | None:
    return (await s.execute(select(SankalpEntry).where(SankalpEntry.company_id == company_id,
                                                       SankalpEntry.idempotency_key == key))).scalar_one_or_none()


def _replay(e: SankalpEntry, user: User, req_hash: str) -> dict:
    if e.original_so_user_id != user.id or e.request_hash != req_hash:
        raise HTTPException(409, {"code": "idempotency_conflict", "message": "Key reused with a different request"})
    return _receipt(e, True)


@router.post("/entries", status_code=201)
async def create_entry(body: EntryIn, user: User = Depends(require_perm("entries.create")),
                       s: AsyncSession = Depends(get_session)):
    received = datetime.now(timezone.utc)
    req_hash = _canon_hash(body)
    if prior := await _existing(s, user.company_id, body.idempotency_key):
        return _replay(prior, user, req_hash)
    # Serialize concurrent retries of the same key: the second waits for the first, then replays its result.
    await s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
                    {"k": f"{user.company_id}:{body.idempotency_key}"})
    if prior := await _existing(s, user.company_id, body.idempotency_key):
        return _replay(prior, user, req_hash)

    if not user.branch_id:
        raise HTTPException(409, {"code": "no_branch", "message": "You are not on the roster of any branch. Ask HR to fix your roster record."})
    errors: list[dict] = []
    name, description = body.person_name.strip(), body.description.strip()
    if not name:
        errors.append({"field": "person_name", "message": "Name of the person met is required"})
    if not description:
        errors.append({"field": "description", "message": "A short description of the meeting is required"})
    phone = clean_phone(body.phone)
    if not is_valid_phone(phone):
        errors.append({"field": "phone", "message": "Enter a valid 10-digit mobile number starting with 6, 7, 8 or 9"})
    subtype = None
    if body.category == "contact_point":
        subtype = await s.get(CpSubtype, body.cp_subtype_id) if body.cp_subtype_id else None
        # Any existing option is accepted (one retired after an offline entry was made is still valid).
        if not subtype or subtype.company_id != user.company_id:
            errors.append({"field": "cp_subtype_id", "message": "Choose the CP sub-type"})
    elif body.cp_subtype_id:
        errors.append({"field": "cp_subtype_id", "message": "CP sub-type is only asked for a Contact Point"})
    loc = body.location
    if (loc.latitude is None) != (loc.longitude is None):
        errors.append({"field": "location", "message": "latitude and longitude must be given together"})
    photos: list[Photo] = []
    if body.photo_ids:
        if len(set(body.photo_ids)) != len(body.photo_ids):
            errors.append({"field": "photo_ids", "message": "A photo is listed twice"})
        photos = list((await s.execute(select(Photo).where(Photo.id.in_(body.photo_ids)))).scalars().all())
        found = {p.id: p for p in photos}
        for pid in body.photo_ids:
            p = found.get(pid)
            if not p or p.user_id != user.id:
                errors.append({"field": "photo_ids", "message": f"Unknown photo {pid}"})
            elif p.upload_status != "complete":
                errors.append({"field": "photo_ids", "message": f"Photo {pid} has not finished uploading"})
            elif p.entry_id is not None or p.submission_id is not None:
                errors.append({"field": "photo_ids", "message": f"Photo {pid} already belongs to another entry"})
    if errors:
        raise HTTPException(422, {"code": "validation_failed", "errors": errors})

    company = await s.get(Company, user.company_id)
    tz = tz_of(company.timezone)
    cfg = await load_settings(s, user.company_id)
    d = calendar.entry_date(body.submitted_at_device, tz)
    holidays = await holiday_set(s, user.company_id, d)
    base_code = calendar.entry_code(user.employee_code.upper(), body.submitted_at_device, tz)
    # Two entries by one SO in the same second: the second gets "-2" (one lock per Entry ID keeps this race-free).
    await s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"{user.company_id}:{base_code}"})
    taken = set((await s.execute(select(SankalpEntry.entry_code).where(
        SankalpEntry.company_id == user.company_id,
        or_(SankalpEntry.entry_code == base_code, SankalpEntry.entry_code.like(f"{base_code}-%"))))).scalars().all())
    code, n = base_code, 1
    while code in taken:
        n += 1
        code = f"{base_code}-{n}"

    has_fix = loc.latitude is not None
    e = SankalpEntry(
        company_id=user.company_id, entry_code=code, emp_code=user.employee_code.upper(),
        so_user_id=user.id, original_so_user_id=user.id, branch_id=user.branch_id, spoke=user.spoke,
        category=body.category, cp_subtype_id=subtype.id if subtype else None,
        cp_subtype_label=subtype.label if subtype else None,
        person_name=name, phone=phone, phone_raw=body.phone.strip()[:50], description=description,
        keka_photo_time=body.keka_photo_time,
        submitted_at_device=body.submitted_at_device, device_tz_offset_min=body.device_tz_offset_min,
        entry_date=d, count_date=calendar.count_date(d, holidays),
        device_time_suspect=body.submitted_at_device > received + timedelta(minutes=cfg.clock_skew_minutes) or bool(
            body.device_clock_at_last_contact
            and body.submitted_at_device < body.device_clock_at_last_contact - timedelta(minutes=1)),
        latitude=loc.latitude, longitude=loc.longitude, accuracy_m=loc.accuracy_m,
        location_fix_at_device=loc.fix_at_device,
        location_status="obtained" if has_fix else (loc.status if loc.status != "obtained" else "unavailable"),
        received_at_server=received, idempotency_key=body.idempotency_key, client_entry_id=body.client_entry_id,
        request_hash=req_hash, photo_count=len(photos), call_group=rules.CALL_GROUP[body.category],
        rag="PENDING" if rules.CALL_GROUP[body.category] != "none" else "NA",
    )
    s.add(e)
    try:
        await s.flush()
        for p in photos:
            p.entry_id = e.id
        s.add(EntryEvent(entry_id=e.id, company_id=user.company_id, kind="created", actor_id=user.id,
                         detail={"entry_code": code, "synced_after_s": round((received - body.submitted_at_device).total_seconds())}))
        s.add(OutboxEvent(company_id=user.company_id, event_type="entry.created",
                          payload={"entry_id": str(e.id), "entry_code": code, "branch_id": str(user.branch_id)}))
        await s.commit()
    except IntegrityError:
        await s.rollback()
        async with SessionLocal() as fresh:  # lost a race with a retry carrying the same key
            prior = await _existing(fresh, user.company_id, body.idempotency_key)
        if prior:
            return _replay(prior, user, req_hash)
        raise
    notify_outbox()
    return _receipt(e, False)


# ---------------------------------------------------------------- reading
def effective_rag(e: SankalpEntry) -> str:
    return e.rag_override or e.rag


def entry_row(e: SankalpEntry, so: User | None, branch: Branch | None, region: Region | None) -> dict:
    return {
        "id": str(e.id), "entry_code": e.entry_code, "emp_code": e.emp_code,
        "so_user_id": str(e.so_user_id), "so_name": so.full_name if so else None,
        "so_employee_code": so.employee_code if so else None,
        "branch_id": str(e.branch_id), "branch_name": branch.name if branch else None,
        "region_name": region.name if region else None,
        "category": e.category, "category_label": rules.CATEGORIES.get(e.category, e.category),
        "cp_subtype_label": e.cp_subtype_label, "call_group": e.call_group,
        "person_name": e.person_name, "phone": e.phone,
        "submitted_at_device": e.submitted_at_device, "received_at_server": e.received_at_server,
        "entry_date": e.entry_date, "count_date": e.count_date, "device_time_suspect": e.device_time_suspect,
        "selection_status": e.selection_status, "status": e.status, "rag": effective_rag(e),
        "rag_overridden": e.rag_override is not None, "priority": e.priority, "priority_reason": e.priority_reason,
        "handling_branch_id": str(e.work_branch_id) if e.work_branch_id else None,
        "expired_action": e.expired_action, "expired_on": e.expired_on,
        "so_action": e.so_action, "so_action_date": e.so_action_date, "so_action_until": e.so_action_until,
        "cc_action": e.cc_action, "cc_action_date": e.cc_action_date,
        "lead_outcome": e.lead_outcome, "tcs_id": e.tcs_id, "customer_validated": e.customer_validated,
        "sankalp_success": e.sankalp_success, "photo_count": e.photo_count,
        "has_location": e.latitude is not None, "place_name": e.place_name,
    }


async def list_query(s: AsyncSession, user: User, *, q=None, branch_id=None, region_id=None, so_user_id=None,
                     category=None, status=None, rag=None, date_from=None, date_to=None, date_field="entry"):
    """The scoped, filtered entry query shared by lists, exports and the map."""
    stmt = (select(SankalpEntry, User, Branch, Region)
            .join(User, User.id == SankalpEntry.so_user_id)
            .join(Branch, Branch.id == SankalpEntry.branch_id)
            .outerjoin(Region, Region.id == Branch.region_id)
            .where(await entry_scope(s, user)))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(SankalpEntry.entry_code.ilike(like), SankalpEntry.person_name.ilike(like),
                              SankalpEntry.phone.like(f"%{clean_phone(q) or q.strip()}%"), User.full_name.ilike(like),
                              User.employee_code.ilike(like)))
    if branch_id:
        stmt = stmt.where(SankalpEntry.branch_id == branch_id)
    if region_id:
        stmt = stmt.where(Branch.region_id == region_id)
    if so_user_id:
        stmt = stmt.where(SankalpEntry.so_user_id == so_user_id)
    if category:
        stmt = stmt.where(SankalpEntry.category.in_(category.split(",")))
    if status:
        wanted = status.split("|")
        conds = [SankalpEntry.status.in_(wanted), SankalpEntry.selection_status.in_(wanted)]
        if "Pending" in wanted:
            conds.append(and_(SankalpEntry.status.is_(None), SankalpEntry.selection_status.is_(None)))
        stmt = stmt.where(or_(*conds))
    if rag:
        stmt = stmt.where(func.coalesce(SankalpEntry.rag_override, SankalpEntry.rag).in_(rag.split(",")))
    col = SankalpEntry.count_date if date_field == "count" else SankalpEntry.entry_date
    if date_from:
        stmt = stmt.where(col >= date_from)
    if date_to:
        stmt = stmt.where(col <= date_to)
    return stmt


@router.get("/entries")
async def list_entries(
    q: str | None = None, branch_id: uuid.UUID | None = None, region_id: uuid.UUID | None = None,
    so_user_id: uuid.UUID | None = None, category: str | None = None, status: str | None = None,
    rag: str | None = None, date_from: str | None = None, date_to: str | None = None,
    date_field: Literal["entry", "count"] = "entry",
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    user: User = Depends(require_perm("entries.read")), s: AsyncSession = Depends(get_session),
):
    try:
        df, dt = parse_date(date_from), parse_date(date_to)
    except ValueError as e:
        raise HTTPException(422, str(e))
    stmt = await list_query(s, user, q=q, branch_id=branch_id, region_id=region_id, so_user_id=so_user_id,
                            category=category, status=status, rag=rag, date_from=df, date_to=dt, date_field=date_field)
    total = (await s.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await s.execute(stmt.order_by(SankalpEntry.submitted_at_device.desc())
                            .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [entry_row(*r) for r in rows], "total": total, "page": page, "page_size": page_size}


async def get_scoped_entry(s: AsyncSession, user: User, entry_id: uuid.UUID) -> SankalpEntry:
    e = (await s.execute(select(SankalpEntry).where(SankalpEntry.id == entry_id, await entry_scope(s, user)))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "Not found")
    return e


def photo_dict(p: Photo) -> dict:
    return {
        "photo_id": str(p.id), "mime_type": p.mime_type, "size_bytes": p.size_bytes, "upload_status": p.upload_status,
        "photo_captured_at_device": p.photo_captured_at_device, "exif_captured_at": p.exif_captured_at,
        "latitude": _f(p.photo_capture_latitude), "longitude": _f(p.photo_capture_longitude),
        "accuracy_m": _f(p.photo_capture_accuracy_m), "location_status": p.photo_location_status,
        "place_name": p.photo_place_name, "place_status": place_status_for_api(p.photo_place_status),
        "url": sign_file_url(str(p.id), "original"), "thumb_url": sign_file_url(str(p.id), "thumb"),
    }


_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


async def readable_history(s: AsyncSession, events) -> list[dict]:
    """The entry's history with people and branches by name. Some events store ids (a wrong-SO correction, the lead
    card's handling branch), which mean nothing to the reader: "new so: Padma Priya", not the id."""
    found: set[str] = set()

    def collect(v):
        if isinstance(v, str) and _UUID.match(v):
            found.add(v)
        elif isinstance(v, (list, dict)):
            for x in (v.values() if isinstance(v, dict) else v):
                collect(x)

    for ev, _ in events:
        collect(ev.detail)
    names: dict[str, str] = {}
    if found:
        ids = [uuid.UUID(x) for x in found]
        for model, label in ((User, User.full_name), (Branch, Branch.name)):
            names.update({str(i): n for i, n in (await s.execute(select(model.id, label).where(model.id.in_(ids)))).all()})

    def named(v):
        if isinstance(v, str):
            return names.get(v, v)
        if isinstance(v, list):
            return [named(x) for x in v]
        if isinstance(v, dict):
            # "handling_branch_id" becomes "handling_branch" once its value is a name
            return {(k.removesuffix("_id") if k.endswith("_id") and _has_named(x, names) else k): named(x) for k, x in v.items()}
        return v

    return [{"kind": ev.kind, "at": ev.created_at, "by": name, "detail": named(ev.detail)} for ev, name in events]


def _has_named(v, names: dict[str, str]) -> bool:
    return v in names if isinstance(v, str) else isinstance(v, list) and any(isinstance(x, str) and x in names for x in v)


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: uuid.UUID, user: User = Depends(require_perm("entries.read")),
                    s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    so = await s.get(User, e.so_user_id)
    branch = await s.get(Branch, e.branch_id)
    region = await s.get(Region, branch.region_id) if branch and branch.region_id else None
    photos = (await s.execute(select(Photo).where(Photo.entry_id == e.id).order_by(Photo.photo_captured_at_device))).scalars().all()
    events = (await s.execute(select(EntryEvent, User.full_name).outerjoin(User, User.id == EntryEvent.actor_id)
                              .where(EntryEvent.entry_id == e.id).order_by(EntryEvent.created_at))).all()
    detail = {
        **entry_row(e, so, branch, region),
        "description": e.description, "keka_photo_time": e.keka_photo_time, "phone_raw": e.phone_raw,
        "device_tz_offset_min": e.device_tz_offset_min, "spoke": e.spoke,
        "location": {"latitude": _f(e.latitude), "longitude": _f(e.longitude), "accuracy_m": _f(e.accuracy_m),
                     "fix_at_device": e.location_fix_at_device, "status": e.location_status,
                     "place_name": e.place_name, "place_status": place_status_for_api(e.place_status)},
        "original_so_user_id": str(e.original_so_user_id), "call_cycle": e.call_cycle,
        "unanswered_count": e.unanswered_count, "callback_date": e.callback_date, "validated_on": e.validated_on,
        "first_validation": e.first_validation, "login_date": e.login_date, "login_source": e.login_source,
        "category_review": e.category_review,
        "photos": [photo_dict(p) for p in photos],
        "history": await readable_history(s, events),
    }
    detail.update(await calling_detail(s, user, e))
    return detail


# ---------------------------------------------------------------- the SO's own day
@router.get("/me/summary")
async def my_summary(user: User = Depends(require_perm("entries.create")), s: AsyncSession = Depends(get_session)):
    """For the app's home screen: today's count against the targets, RAG of the last 30 days, numbers to correct."""
    today = await company_today(s, user.company_id)
    cfg = await load_settings(s, user.company_id)
    mine = and_(SankalpEntry.company_id == user.company_id, SankalpEntry.so_user_id == user.id)
    today_rows = (await s.execute(select(SankalpEntry.category, func.count()).where(mine, SankalpEntry.count_date == today)
                                  .group_by(SankalpEntry.category))).all()
    by_cat = dict(today_rows)
    rag_rows = (await s.execute(select(func.coalesce(SankalpEntry.rag_override, SankalpEntry.rag), func.count())
                                .where(mine, SankalpEntry.entry_date >= today - timedelta(days=30))
                                .group_by(func.coalesce(SankalpEntry.rag_override, SankalpEntry.rag)))).all()
    holidays = sorted((await s.execute(select(Holiday.day).where(
        Holiday.company_id == user.company_id, Holiday.day >= today - timedelta(days=7),
        Holiday.day <= today + timedelta(days=90)))).scalars().all())
    fix = (await s.execute(select(SankalpEntry).where(
        mine, SankalpEntry.so_action == rules.ACT_CORRECT_NUMBER,
        or_(SankalpEntry.so_action_until.is_(None), SankalpEntry.so_action_until >= today))
        .order_by(SankalpEntry.entry_date.desc()).limit(50))).scalars().all()
    return {
        "today": today, "entries_today": sum(by_cat.values()),
        "lead_prospect_today": sum(v for k, v in by_cat.items() if k in rules.LEAD_CATEGORIES),
        "by_category_today": by_cat, "entry_target": cfg.daily_entry_target, "lead_target": cfg.daily_lead_target,
        "correct_number_window_days": cfg.amber_correction_window_days,
        # the app counts entries still waiting on the phone by their count date too (Sundays and these days move on)
        "holidays": holidays,
        "rag_last_30_days": dict(rag_rows),
        "correct_number": [{"id": str(e.id), "entry_code": e.entry_code, "person_name": e.person_name, "phone": e.phone,
                            "until": e.so_action_until, "status": e.status} for e in fix],
    }
