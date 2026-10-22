"""Data for the Live Field Activity Map.

The markers are the GPS positions RECORDED when an agent pressed Submit (and, optionally, when each photo was taken).
This is event data, not live tracking: the app does not follow agents around.
"""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.api.v1.submissions import _base_query, apply_filters
from app.core.db import get_session
from app.models import Branch, Company, Submission, SubmissionPhoto, SubmissionPhotoLink, SubmissionPersonType, User
from app.services.geocoding import place_status_for_api

router = APIRouter(prefix="/map", tags=["map"])
MAX_MARKERS = 2000


def _f(v):
    return None if v is None else float(v)


def _meeting_dates(answers: dict) -> list[str]:
    """Meeting dates entered in the report (the repeatable section's `meeting_date` field)."""
    out = []
    for sec in (answers or {}).values():
        for entry in (sec if isinstance(sec, list) else [sec]):
            if isinstance(entry, dict) and isinstance(entry.get("meeting_date"), str):
                out.append(entry["meeting_date"])
    return sorted(set(out))


@router.get("/markers")
async def markers(
    date_from: date | None = None, date_to: date | None = None, branch_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None, form_id: str | None = None,
    review_status: Literal["pending", "approved", "rejected"] | None = None,
    person_type_id: uuid.UUID | None = None, latest_only: bool = True,
    include_photos: bool = False, include_branches: bool = True,
    admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session),
):
    company = await s.get(Company, admin.company_id)
    base = apply_filters(_base_query(), company=company, date_from=date_from, date_to=date_to, branch_id=branch_id,
                         agent_id=agent_id, form_id=form_id, status=None, review_status=review_status, has_location=None,
                         person_type_id=person_type_id, latest_only=latest_only, reference=None)
    total = (await s.execute(select(func.count()).select_from(base.with_only_columns(Submission.id).order_by(None).subquery()))).scalar_one()
    with_gps = (await s.execute(select(func.count()).select_from(
        base.where(Submission.submission_latitude.is_not(None)).with_only_columns(Submission.id).order_by(None).subquery()))).scalar_one()

    rows = (await s.execute(base.where(Submission.submission_latitude.is_not(None), Submission.submission_longitude.is_not(None))
                            .order_by(Submission.accepted_at_server.desc()).limit(MAX_MARKERS))).all()
    reports = []
    for sub, agent, code, branch, form_title, _v in rows:
        reports.append({
            "id": str(sub.id), "reference": sub.reference, "revision": sub.revision, "agent_name": agent, "employee_code": code,
            "branch_id": str(sub.branch_id) if sub.branch_id else None, "branch_name": branch, "form_title": form_title,
            "review_status": sub.review_status, "latitude": _f(sub.submission_latitude), "longitude": _f(sub.submission_longitude),
            "accuracy_m": _f(sub.submission_accuracy_m), "location_status": sub.submission_location_status,
            "place_name": sub.submission_place_name, "place_status": place_status_for_api(sub.submission_place_status),
            "submitted_at_device": sub.submitted_at_device, "accepted_at_server": sub.accepted_at_server,
            "meeting_dates": _meeting_dates(sub.answers), "person_types": list(dict.fromkeys((sub.option_labels or {}).values())),
        })

    photos = []
    if include_photos and rows:
        ids = [r[0].id for r in rows]
        by_sub = {r[0].id: r for r in rows}
        for p, link in (await s.execute(
            select(SubmissionPhoto, SubmissionPhotoLink).join(SubmissionPhotoLink, SubmissionPhotoLink.photo_id == SubmissionPhoto.id)
            .where(SubmissionPhotoLink.submission_id.in_(ids), SubmissionPhoto.photo_capture_latitude.is_not(None))
            .limit(MAX_MARKERS))).all():
            sub, agent, _c, branch, _t, _v = by_sub[link.submission_id]
            photos.append({
                "id": str(p.id), "submission_id": str(sub.id), "reference": sub.reference, "agent_name": agent, "branch_name": branch,
                "review_status": sub.review_status, "latitude": _f(p.photo_capture_latitude), "longitude": _f(p.photo_capture_longitude),
                "accuracy_m": _f(p.photo_capture_accuracy_m), "place_name": p.photo_place_name,
                "place_status": place_status_for_api(p.photo_place_status), "captured_at_device": p.photo_captured_at_device,
            })

    branches = []
    if include_branches:
        q = select(Branch).where(Branch.company_id == company.id, Branch.latitude.is_not(None), Branch.longitude.is_not(None))
        if branch_id:
            q = q.where(Branch.id == branch_id)
        branches = [{"id": str(b.id), "name": b.name, "code": b.code, "status": b.status,
                     "latitude": _f(b.latitude), "longitude": _f(b.longitude)} for b in (await s.execute(q)).scalars().all()]
    return {
        "reports": reports, "photos": photos, "branches": branches,
        "counts": {"reports": total, "with_gps": with_gps, "without_gps": total - with_gps, "shown": len(reports),
                   "truncated": with_gps > len(reports)},
        "note": "Positions are recorded when Submit is pressed or a photo is taken; this is not live tracking.",
    }
