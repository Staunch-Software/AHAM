"""Review workflow: configurable rejection reasons, approve / reject (with reason, comment and flags), reopen,
and the feed the agent app uses to learn about decisions."""
import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_roles
from app.core.db import get_session
from app.models import OutboxEvent, ReviewReason, Submission, SubmissionEvent, SubmissionReview, User
from app.services.workflow import audit, ensure_company_defaults
from app.workers.outbox import notify_outbox

router = APIRouter(tags=["review"])
require_agent = require_roles("agent")


# ---------------------------------------------------------------- rejection reasons (configurable)
class ReasonIn(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    default_message: str | None = Field(None, max_length=500)
    requires_comment: bool = False


class ReasonPatch(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    default_message: str | None = Field(None, max_length=500)
    requires_comment: bool | None = None
    active: bool | None = None


class OrderIn(BaseModel):
    ids: list[uuid.UUID]


def _reason_dict(r: ReviewReason) -> dict:
    return {"id": str(r.id), "code": r.code, "label": r.label, "default_message": r.default_message,
            "requires_comment": r.requires_comment, "active": r.active, "sort_order": r.sort_order}


async def _reasons(s: AsyncSession, company_id: uuid.UUID) -> list[ReviewReason]:
    return list((await s.execute(select(ReviewReason).where(ReviewReason.company_id == company_id)
                                 .order_by(ReviewReason.sort_order, ReviewReason.label))).scalars().all())


@router.get("/review-reasons")
async def list_reasons(admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    await ensure_company_defaults(s, admin.company_id)
    await s.commit()
    return {"items": [_reason_dict(r) for r in await _reasons(s, admin.company_id)]}


@router.post("/review-reasons", status_code=201)
async def add_reason(body: ReasonIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    label = body.label.strip()
    code = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40] or "reason"
    existing = {r.code for r in await _reasons(s, admin.company_id)}
    base, n = code, 2
    while code in existing:
        code, n = f"{base}_{n}", n + 1
    top = (await s.execute(select(func.coalesce(func.max(ReviewReason.sort_order), -1)).where(ReviewReason.company_id == admin.company_id))).scalar_one()
    r = ReviewReason(company_id=admin.company_id, code=code, label=label, default_message=body.default_message,
                     requires_comment=body.requires_comment, sort_order=top + 1)
    s.add(r)
    await s.flush()
    audit(s, admin, "review_reason.create", "review_reason", r.id)
    await s.commit()
    return {"items": [_reason_dict(x) for x in await _reasons(s, admin.company_id)]}


@router.put("/review-reasons/order")
async def reorder_reasons(body: OrderIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    rs = {r.id: r for r in await _reasons(s, admin.company_id)}
    if len(set(body.ids)) != len(body.ids) or not set(body.ids) <= set(rs):
        raise HTTPException(422, "Unknown or repeated reason id")
    for pos, rid in enumerate(body.ids):
        rs[rid].sort_order = pos
    for i, r in enumerate(sorted((r for rid, r in rs.items() if rid not in set(body.ids)), key=lambda r: r.sort_order), start=len(body.ids)):
        r.sort_order = i
    audit(s, admin, "review_reason.reorder", "company", admin.company_id)
    await s.commit()
    return {"items": [_reason_dict(x) for x in await _reasons(s, admin.company_id)]}


@router.patch("/review-reasons/{reason_id}")
async def update_reason(reason_id: uuid.UUID, body: ReasonPatch, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    r = await s.get(ReviewReason, reason_id)
    if not r or r.company_id != admin.company_id:
        raise HTTPException(404, "Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v.strip() if isinstance(v, str) else v)
    audit(s, admin, "review_reason.update", "review_reason", r.id)
    await s.commit()
    return {"items": [_reason_dict(x) for x in await _reasons(s, admin.company_id)]}


# ---------------------------------------------------------------- decisions
class FlagIn(BaseModel):
    path: str = Field(min_length=1, max_length=200)  # e.g. meeting_details[1] or meeting_details[1].meeting_photos
    note: str = Field(min_length=1, max_length=300)


class ReviewIn(BaseModel):
    decision: Literal["approved", "rejected"]
    reason_code: str | None = None
    comment: str | None = Field(None, max_length=2000)
    flags: list[FlagIn] = Field(default_factory=list, max_length=30)


class ReopenIn(BaseModel):
    comment: str = Field(min_length=3, max_length=2000)


def _review_block(sub: Submission) -> dict:
    return {"status": sub.review_status, "reason_code": sub.review_reason_code, "comment": sub.review_comment,
            "flags": sub.review_flags or [], "reviewed_at": sub.reviewed_at}


async def _reviewable(s: AsyncSession, admin: User, submission_id: uuid.UUID) -> Submission:
    sub = await s.get(Submission, submission_id)
    if not sub or sub.company_id != admin.company_id:
        raise HTTPException(404, "Not found")
    return sub


def _record(s: AsyncSession, sub: Submission, admin: User, decision: str, reason: ReviewReason | None,
            comment: str | None, flags: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    sub.review_status = {"approved": "approved", "rejected": "rejected", "reopened": "pending"}[decision]
    sub.reviewed_by, sub.reviewed_at = admin.id, now
    sub.review_reason_code = reason.code if reason else None
    sub.review_comment = comment
    sub.review_flags = flags
    s.add(SubmissionReview(submission_id=sub.id, company_id=sub.company_id, reviewer_id=admin.id, decision=decision,
                           reason_code=reason.code if reason else None, reason_label=reason.label if reason else None,
                           comment=comment, flags=flags))
    s.add(SubmissionEvent(submission_id=sub.id, event_type=f"review.{decision}", detail=str(admin.id)))
    s.add(OutboxEvent(company_id=sub.company_id, event_type="submission.reviewed",
                      payload={"submission_id": str(sub.id), "decision": decision, "reference": sub.reference}))
    audit(s, admin, f"review.{decision}", "submission", sub.id)


@router.post("/submissions/{submission_id}/reviews")
async def decide(submission_id: uuid.UUID, body: ReviewIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    sub = await _reviewable(s, admin, submission_id)
    if not sub.is_latest:
        raise HTTPException(409, "A newer version of this report exists. Review the latest version.")
    if sub.review_status == "approved":
        raise HTTPException(409, "Approved reports are final. Use Reopen (with a reason) to review it again.")
    reason = None
    comment = (body.comment or "").strip() or None
    if body.decision == "rejected":
        if not body.reason_code:
            raise HTTPException(422, "A reason is required to reject a report")
        reason = (await s.execute(select(ReviewReason).where(
            ReviewReason.company_id == admin.company_id, ReviewReason.code == body.reason_code, ReviewReason.active))).scalar_one_or_none()
        if not reason:
            raise HTTPException(422, "Unknown or inactive rejection reason")
        if reason.requires_comment and not comment:
            raise HTTPException(422, f"Please explain: '{reason.label}' needs a written comment")
    flags = [f.model_dump() for f in body.flags] if body.decision == "rejected" else []
    _record(s, sub, admin, body.decision, reason, comment, flags)
    await s.commit()
    notify_outbox()
    return _review_block(sub)


@router.post("/submissions/{submission_id}/reopen")
async def reopen(submission_id: uuid.UUID, body: ReopenIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    """Controlled way to review an approved report again; the original decision stays in the history."""
    sub = await _reviewable(s, admin, submission_id)
    if sub.review_status != "approved" or not sub.is_latest:
        raise HTTPException(409, "Only the latest, approved version of a report can be reopened")
    _record(s, sub, admin, "reopened", None, body.comment.strip(), [])
    await s.commit()
    notify_outbox()
    return _review_block(sub)


# ---------------------------------------------------------------- feed for the agent app
@router.get("/agent/reports/updates")
async def agent_updates(since: datetime | None = Query(None), user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)):
    """The agent's reports that were reviewed after `since` (all of them when omitted), with the latest decision."""
    q = select(Submission).where(Submission.company_id == user.company_id, Submission.user_id == user.id,
                                 Submission.reviewed_at.is_not(None))
    if since:
        q = q.where(Submission.reviewed_at > since)
    subs = (await s.execute(q.order_by(Submission.reviewed_at).limit(200))).scalars().all()
    latest: dict[uuid.UUID, SubmissionReview] = {}
    if subs:
        for rv in (await s.execute(select(SubmissionReview).where(SubmissionReview.submission_id.in_([x.id for x in subs]))
                                   .order_by(SubmissionReview.created_at))).scalars():
            latest[rv.submission_id] = rv  # ascending order: the last one wins
    return {"items": [
        {"id": str(x.id), "reference": x.reference, "revision": x.revision, "is_latest": x.is_latest,
         "review_status": x.review_status, "reason_code": x.review_reason_code,
         "reason_label": latest[x.id].reason_label if x.id in latest else None,
         "comment": x.review_comment, "flags": x.review_flags or [], "reviewed_at": x.reviewed_at}
        for x in subs]}
