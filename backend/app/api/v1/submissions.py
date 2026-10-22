import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_admin, require_roles
from app.api.v1.forms import accessible_forms, agent_branch_ids
from app.api.v1.uploads import LocationStatus, photo_dict
from app.core.db import SessionLocal, get_session
from app.models import (
    Branch,
    Company,
    FormDefinition,
    FormVersion,
    OutboxEvent,
    PersonType,
    Submission,
    SubmissionEvent,
    SubmissionPersonType,
    SubmissionPhoto,
    SubmissionPhotoLink,
    SubmissionReview,
    User,
)
from app.services.form_schema import collect_photo_refs, dynamic_entries, validate_answers
from app.services.geocoding import place_status_for_api
from app.services.periods import day_range_utc, tz_of
from app.services.workflow import load_person_types, next_reference, overlay_for_company
from app.workers.outbox import notify_outbox

router = APIRouter(tags=["submissions"])
require_agent = require_roles("agent")


class SubmissionLocation(BaseModel):
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    accuracy_m: float | None = Field(None, ge=0, le=100000)
    fix_at_device: datetime | None = None
    status: LocationStatus = "unavailable"


class CorrectsIn(BaseModel):
    """Marks this submission as the corrected version of a report that was sent back for correction."""

    submission_id: uuid.UUID  # the revision being corrected (its server id, from the earlier receipt)
    base_revision: int = Field(ge=1)  # the revision number the agent saw; guards against stale or duplicate corrections


class SubmissionIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    client_submission_id: str = Field(min_length=1, max_length=100)
    form_id: str
    form_version: int = Field(ge=1)
    branch_id: uuid.UUID | None = None
    answers: dict
    submitted_at_device: datetime
    device_tz_offset_min: int | None = Field(None, ge=-840, le=840)
    location: SubmissionLocation = SubmissionLocation()
    corrects: CorrectsIn | None = None


def _f(v):
    return None if v is None else float(v)


def _receipt(sub: Submission, duplicate: bool) -> dict:
    return {
        "id": str(sub.id), "client_submission_id": sub.client_submission_id, "status": sub.status,
        "received_at_server": sub.received_at_server, "accepted_at_server": sub.accepted_at_server,
        "reference": sub.reference, "revision": sub.revision, "root_id": str(sub.root_id),
        "duplicate": duplicate,
    }


def _canon_hash(body: SubmissionIn) -> str:
    raw = json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


async def _existing(s: AsyncSession, user: User, key: str) -> Submission | None:
    return (
        await s.execute(
            select(Submission).where(Submission.company_id == user.company_id, Submission.idempotency_key == key)
        )
    ).scalar_one_or_none()


def _replay(sub: Submission, user: User, req_hash: str) -> dict:
    if sub.user_id != user.id or sub.request_hash != req_hash:
        raise HTTPException(409, {"code": "idempotency_conflict", "message": "Key reused with a different request"})
    return _receipt(sub, True)


async def _check_correction(s: AsyncSession, user: User, c: CorrectsIn, fv: FormVersion) -> Submission:
    """The report being corrected must be the agent's own, still the newest revision, and sent back for correction."""
    prev = await s.get(Submission, c.submission_id)
    if not prev or prev.company_id != user.company_id or prev.user_id != user.id:
        raise HTTPException(404, {"code": "report_not_found", "message": "The report to correct was not found"})
    # one correction at a time per report: the second of two concurrent corrections waits, then sees the change
    await s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"root:{prev.root_id}"})
    latest = (
        await s.execute(
            select(Submission).where(Submission.root_id == prev.root_id, Submission.is_latest)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    if latest.id != prev.id or latest.revision != c.base_revision:
        raise HTTPException(409, {"code": "report_changed", "message": (
            f"This report was changed on the server (now revision {latest.revision}). "
            "Open it again to see the latest version before correcting it.")})
    if latest.review_status != "rejected":
        raise HTTPException(409, {"code": "report_not_rejected", "message": (
            f"This report is '{latest.review_status}', so it cannot be corrected. "
            "Only reports that were sent back for correction can be resubmitted.")})
    if latest.form_version_id != fv.id:
        raise HTTPException(409, {"code": "form_version_mismatch", "message": "A correction must use the same form version as the original report"})
    return latest


@router.post("/submissions", status_code=201)
async def create_submission(body: SubmissionIn, user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)):
    received = datetime.now(timezone.utc)
    req_hash = _canon_hash(body)
    if prior := await _existing(s, user, body.idempotency_key):
        return _replay(prior, user, req_hash)
    # Serialize concurrent requests carrying the same key: the second waits here until the first commits,
    # then replays its result: no failed INSERT / rolled-back transaction in the common retry race.
    await s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
                    {"k": f"{user.company_id}:{body.idempotency_key}"})
    if prior := await _existing(s, user, body.idempotency_key):
        return _replay(prior, user, req_hash)

    forms = {f.key: f for f in await accessible_forms(s, user)}
    form = forms.get(body.form_id)
    if not form:
        raise HTTPException(403, {"code": "form_not_assigned", "message": "Form not available to this agent"})
    fv = (
        await s.execute(select(FormVersion).where(FormVersion.form_id == form.id, FormVersion.version == body.form_version))
    ).scalar_one_or_none()
    if not fv or fv.status == "retired":
        raise HTTPException(409, {"code": "schema_outdated", "message": "Form version no longer accepted"})

    allowed = await agent_branch_ids(s, user)
    branch_id = body.branch_id or user.branch_id
    if branch_id is not None and branch_id not in allowed:
        raise HTTPException(403, {"code": "branch_not_permitted", "message": "Branch not permitted"})

    prev = await _check_correction(s, user, body.corrects, fv) if body.corrects else None

    # Validate against the schema with the company's CURRENT managed options (every existing option id is accepted,
    # even a since-retired one, so a report written offline before an option was retired is still valid).
    eff_schema = await overlay_for_company(s, user.company_id, fv.schema, delivery=False)
    errors = validate_answers(eff_schema, body.answers)
    loc = body.location
    if (loc.latitude is None) != (loc.longitude is None):
        errors.append({"field_id": "location", "path": "location", "message": "latitude/longitude must be paired"})

    refs = collect_photo_refs(fv.schema, body.answers) if not errors else []
    photos: dict[uuid.UUID, SubmissionPhoto] = {}
    if refs:
        ids = [uuid.UUID(r["photo_id"]) for r in refs]
        if len(set(ids)) != len(ids):
            errors.append({"field_id": None, "path": "answers", "message": "photo used more than once"})
        rows = (
            await s.execute(select(SubmissionPhoto).where(SubmissionPhoto.id.in_(ids), SubmissionPhoto.company_id == user.company_id))
        ).scalars().all()
        photos = {p.id: p for p in rows}
        # which report revisions each photo is already attached to
        links: dict[uuid.UUID, set[uuid.UUID]] = {}
        for pid, sid in (await s.execute(select(SubmissionPhotoLink.photo_id, SubmissionPhotoLink.submission_id)
                                         .where(SubmissionPhotoLink.photo_id.in_(ids)))).all():
            links.setdefault(pid, set()).add(sid)
        lineage = set()
        if prev:
            lineage = set((await s.execute(select(Submission.id).where(Submission.root_id == prev.root_id))).scalars().all())
        for r in refs:
            pid = uuid.UUID(r["photo_id"])
            p = photos.get(pid)
            path = f"{r['group_key']}.{r['field']}"
            if not p or p.user_id != user.id:
                errors.append({"field_id": r["field"], "path": path, "message": "unknown photo"})
            elif p.upload_status != "complete":
                errors.append({"field_id": r["field"], "path": path, "message": "photo upload not complete"})
            elif links.get(pid) and not links[pid] <= lineage:
                # attached to some other report; photos kept from the report being corrected are fine
                errors.append({"field_id": r["field"], "path": path, "message": "photo already attached"})
    if errors:
        raise HTTPException(422, {"code": "validation_failed", "errors": errors})

    # Managed option picks (type of person): keep the label as it is right now, and a row per meeting for analytics.
    types = {t.id: t for t in await load_person_types(s, user.company_id)}
    option_labels: dict[str, str] = {}
    person_rows: list[SubmissionPersonType] = []
    for path, source, value in dynamic_entries(eff_schema, body.answers):
        if source != "person_types":
            continue
        if value.startswith("other:"):
            other = value[6:].strip()
            option_labels[path] = other
            person_rows.append(SubmissionPersonType(company_id=user.company_id, entry_path=path, other_text=other, label_snapshot=other))
        else:
            t = types[uuid.UUID(value)]  # validated above
            option_labels[path] = t.label
            person_rows.append(SubmissionPersonType(company_id=user.company_id, entry_path=path, person_type_id=t.id, label_snapshot=t.label))

    has_fix = loc.latitude is not None
    accepted = datetime.now(timezone.utc)
    new_id = uuid.uuid4()
    sub = Submission(
        id=new_id, company_id=user.company_id, user_id=user.id, branch_id=branch_id, form_version_id=fv.id,
        idempotency_key=body.idempotency_key, client_submission_id=body.client_submission_id,
        request_hash=req_hash, answers=body.answers, submitted_at_device=body.submitted_at_device,
        device_tz_offset_min=body.device_tz_offset_min,
        submission_latitude=loc.latitude, submission_longitude=loc.longitude,
        submission_accuracy_m=loc.accuracy_m, submission_location_fix_at_device=loc.fix_at_device,
        submission_location_status="obtained" if has_fix else (loc.status if loc.status != "obtained" else "unavailable"),
        received_at_server=received, accepted_at_server=accepted, photo_count=len(refs),
        root_id=prev.root_id if prev else new_id, revision=prev.revision + 1 if prev else 1, is_latest=True,
        corrects_id=prev.id if prev else None, option_labels=option_labels or None,
        reference=prev.reference if prev else await next_reference(s, user.company_id, accepted),
    )
    s.add(sub)
    try:
        if prev:
            prev.is_latest = False  # the earlier revision stays as history, never edited
        await s.flush()
        for r in refs:
            p = photos[uuid.UUID(r["photo_id"])]
            s.add(SubmissionPhotoLink(submission_id=sub.id, photo_id=p.id, group_key=r["group_key"], field_key=r["field"]))
            if p.submission_id is None:
                p.submission_id, p.group_key, p.field_key = sub.id, r["group_key"], r["field"]
        for pr in person_rows:
            pr.submission_id = sub.id
            s.add(pr)
        s.add(SubmissionEvent(submission_id=sub.id, event_type="resubmitted" if prev else "accepted",
                              detail=f"revision {sub.revision}" if prev else None))
        s.add(OutboxEvent(
            company_id=user.company_id, event_type="submission.resubmitted" if prev else "submission.accepted",
            payload={"submission_id": str(sub.id), "branch_id": str(branch_id) if branch_id else None,
                     "reference": sub.reference, "revision": sub.revision},
        ))
        await s.commit()
    except IntegrityError:
        # Lost a race with a concurrent retry carrying the same idempotency key.
        await s.rollback()
        async with SessionLocal() as fresh:  # never reuse the rolled-back session
            prior = await _existing(fresh, user, body.idempotency_key)
        if prior:
            return _replay(prior, user, req_hash)
        raise
    notify_outbox()
    return _receipt(sub, False)


def _row(sub, name, code, branch, form_title, form_version, types=None) -> dict:
    return {
        "id": str(sub.id), "agent_name": name, "employee_code": code, "branch_id": sub.branch_id and str(sub.branch_id),
        "branch_name": branch, "form_title": form_title, "form_version": form_version,
        "submitted_at_device": sub.submitted_at_device, "received_at_server": sub.received_at_server,
        "accepted_at_server": sub.accepted_at_server, "status": sub.status, "review_status": sub.review_status,
        "photo_count": sub.photo_count, "has_location": sub.submission_latitude is not None,
        "reference": sub.reference, "revision": sub.revision, "is_latest": sub.is_latest, "root_id": str(sub.root_id),
        "person_types": types or [],
        "review_reason_code": sub.review_reason_code, "review_comment": sub.review_comment,
        "review_flags": sub.review_flags or [], "reviewed_at": sub.reviewed_at,
    }


def _base_query():
    return (
        select(Submission, User.full_name, User.employee_code, Branch.name, FormDefinition.title, FormVersion.version)
        .join(User, User.id == Submission.user_id)
        .outerjoin(Branch, Branch.id == Submission.branch_id)
        .join(FormVersion, FormVersion.id == Submission.form_version_id)
        .join(FormDefinition, FormDefinition.id == FormVersion.form_id)
    )


async def _page(s: AsyncSession, q, page: int, size: int) -> dict:
    total = (await s.execute(select(func.count()).select_from(q.with_only_columns(Submission.id).order_by(None).subquery()))).scalar_one()
    rows = (
        await s.execute(q.order_by(Submission.accepted_at_server.desc(), Submission.id).offset((page - 1) * size).limit(size))
    ).all()
    labels: dict[uuid.UUID, list[str]] = {}
    if rows:
        for sid, label in (await s.execute(
                select(SubmissionPersonType.submission_id, SubmissionPersonType.label_snapshot)
                .where(SubmissionPersonType.submission_id.in_([r[0].id for r in rows]))
                .order_by(SubmissionPersonType.entry_path))).all():
            if label not in labels.setdefault(sid, []):
                labels[sid].append(label)
    return {"items": [_row(*r, types=labels.get(r[0].id)) for r in rows], "total": total, "page": page, "page_size": size}


def apply_filters(q, *, company: Company, date_from, date_to, branch_id, agent_id, form_id, status, review_status,
                  has_location, person_type_id, latest_only, reference):
    """Shared by the submissions list and the map so both always filter identically."""
    start, end = day_range_utc(date_from, date_to, tz_of(company.timezone))
    q = q.where(Submission.company_id == company.id)
    if start:
        q = q.where(Submission.accepted_at_server >= start)
    if end:
        q = q.where(Submission.accepted_at_server < end)
    if branch_id:
        q = q.where(Submission.branch_id == branch_id)
    if agent_id:
        q = q.where(Submission.user_id == agent_id)
    if form_id:
        q = q.where(FormDefinition.key == form_id)
    if status:
        q = q.where(Submission.status == status)
    if review_status:
        q = q.where(Submission.review_status == review_status)
    if has_location is not None:
        q = q.where(Submission.submission_latitude.is_not(None) if has_location else Submission.submission_latitude.is_(None))
    if person_type_id:
        q = q.where(exists().where(SubmissionPersonType.submission_id == Submission.id,
                                   SubmissionPersonType.person_type_id == person_type_id))
    if latest_only:
        q = q.where(Submission.is_latest)
    if reference:
        q = q.where(Submission.reference.ilike(f"%{reference.strip()}%"))
    return q


@router.get("/submissions")
async def list_submissions(
    date_from: date | None = None, date_to: date | None = None, branch_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None, form_id: str | None = None,
    status: str | None = None, review_status: Literal["pending", "approved", "rejected"] | None = None,
    has_location: bool | None = None, person_type_id: uuid.UUID | None = None,
    latest_only: bool = True, reference: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session),
):
    company = await s.get(Company, admin.company_id)
    q = apply_filters(_base_query(), company=company, date_from=date_from, date_to=date_to, branch_id=branch_id,
                      agent_id=agent_id, form_id=form_id, status=status, review_status=review_status,
                      has_location=has_location, person_type_id=person_type_id, latest_only=latest_only, reference=reference)
    return await _page(s, q, page, page_size)


@router.get("/agent/submissions")
async def my_submissions(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(require_agent), s: AsyncSession = Depends(get_session),
):
    q = _base_query().where(Submission.company_id == user.company_id, Submission.user_id == user.id)
    return await _page(s, q, page, page_size)


@router.get("/submissions/{submission_id}")
async def submission_detail(submission_id: uuid.UUID, user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    row = (await s.execute(_base_query().where(Submission.id == submission_id, Submission.company_id == user.company_id))).first()
    if not row or (user.role != "admin" and row[0].user_id != user.id):
        raise HTTPException(404, "Not found")
    sub = row[0]
    fv = await s.get(FormVersion, sub.form_version_id)
    pairs = (
        await s.execute(
            select(SubmissionPhoto, SubmissionPhotoLink)
            .join(SubmissionPhotoLink, SubmissionPhotoLink.photo_id == SubmissionPhoto.id)
            .where(SubmissionPhotoLink.submission_id == sub.id)
        )
    ).all()
    events = (
        await s.execute(select(SubmissionEvent).where(SubmissionEvent.submission_id == sub.id).order_by(SubmissionEvent.created_at))
    ).scalars().all()
    revisions = (
        await s.execute(select(Submission).where(Submission.root_id == sub.root_id, Submission.company_id == user.company_id)
                        .order_by(Submission.revision))
    ).scalars().all()
    rev_no = {r.id: r.revision for r in revisions}
    reviews = (
        await s.execute(
            select(SubmissionReview, User.full_name).join(User, User.id == SubmissionReview.reviewer_id)
            .where(SubmissionReview.submission_id.in_(list(rev_no)))
            .order_by(SubmissionReview.created_at)
        )
    ).all()
    types = [t for t in (sub.option_labels or {}).values()]
    return {
        **_row(*row, types=list(dict.fromkeys(types))),
        "answers": sub.answers, "schema": fv.schema, "client_submission_id": sub.client_submission_id,
        "option_labels": sub.option_labels or {},
        "device_tz_offset_min": sub.device_tz_offset_min,
        "submission_location": {
            "latitude": _f(sub.submission_latitude), "longitude": _f(sub.submission_longitude),
            "accuracy_m": _f(sub.submission_accuracy_m), "fix_at_device": sub.submission_location_fix_at_device,
            "status": sub.submission_location_status,
            "place_name": sub.submission_place_name, "place_status": place_status_for_api(sub.submission_place_status),
        },
        "photos": [photo_dict(p, link) for p, link in pairs],
        "events": [{"type": e.event_type, "detail": e.detail, "at": e.created_at} for e in events],
        "revisions": [{"id": str(r.id), "revision": r.revision, "accepted_at_server": r.accepted_at_server,
                       "review_status": r.review_status, "is_latest": r.is_latest} for r in revisions],
        "reviews": [{"id": str(rv.id), "submission_id": str(rv.submission_id), "revision": rev_no[rv.submission_id],
                     "decision": rv.decision, "reason_code": rv.reason_code, "reason_label": rv.reason_label,
                     "comment": rv.comment, "flags": rv.flags or [], "reviewer": name, "created_at": rv.created_at}
                    for rv, name in reviews],
    }
