"""Branch and agent performance analytics, computed on the server for a chosen period.

Definitions (also shown in the admin web):
  * Reports submitted  = reports first submitted in the period (revision 1). A corrected resubmission is NOT counted twice.
  * Pending / approved / needs correction = the CURRENT state of those reports (their newest revision).
  * Rejection rate     = rejections / (approvals + rejections) among review decisions MADE in the period.
                         Pending reports never enter the calculation.
  * Target achievement = reports submitted / configured target x 100, only for week and month periods and only
                         when a target is set (targets are optional until the business confirms its rules).
  * Trend              = reports submitted compared with the previous equivalent period.
"""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.deps import require_admin
from app.core.db import get_session
from app.models import (
    Branch,
    Company,
    ReportTarget,
    Submission,
    SubmissionPersonType,
    SubmissionReview,
    User,
    UserBranchAssignment,
)
from app.services.periods import period_bounds, previous_bounds, tz_of
from app.services.workflow import audit

router = APIRouter(prefix="/analytics", tags=["analytics"])
Period = Literal["today", "week", "month", "custom"]


def _pct(num: float, den: float) -> float | None:
    return None if not den else round(100.0 * num / den, 1)


def _trend(cur: int, prev: int) -> float | None:
    """Change vs the previous period in %, or None when there is nothing to compare with."""
    return None if prev == 0 else round(100.0 * (cur - prev) / prev, 1)


class Ctx:
    def __init__(self, company: Company, period: str, date_from: date | None, date_to: date | None):
        self.company = company
        self.tz = tz_of(company.timezone)
        self.period = period
        self.start, self.end, self.first, self.last = period_bounds(period, self.tz, date_from, date_to)
        self.prev_start, self.prev_end = previous_bounds(self.first, self.last, self.tz, period)
        # targets are per week/month: meaningless for "today" or an arbitrary custom range
        self.target_period = {"week": "weekly", "month": "monthly"}.get(period)

    def meta(self) -> dict:
        return {"key": self.period, "from": self.first.isoformat(), "to": self.last.isoformat(),
                "timezone": self.company.timezone, "targets_apply": self.target_period is not None}


async def _agents_by_branch(s: AsyncSession, cid: uuid.UUID) -> dict[uuid.UUID, set[uuid.UUID]]:
    out: dict[uuid.UUID, set[uuid.UUID]] = {}
    agents = (await s.execute(select(User.id, User.branch_id).where(User.company_id == cid, User.role == "agent",
                                                                    User.status == "active"))).all()
    active = {a.id for a in agents}
    for a in agents:
        if a.branch_id:
            out.setdefault(a.branch_id, set()).add(a.id)
    for uid, bid in (await s.execute(select(UserBranchAssignment.user_id, UserBranchAssignment.branch_id)
                                     .join(User, User.id == UserBranchAssignment.user_id)
                                     .where(User.company_id == cid))).all():
        if uid in active:
            out.setdefault(bid, set()).add(uid)
    return out


async def _status_counts(s: AsyncSession, ctx: Ctx, group_col):
    """Current review state of reports first submitted in the period, grouped by branch or agent."""
    R = aliased(Submission)  # the first revision (id == root_id) fixes when the report was submitted
    col = getattr(Submission, group_col)
    rows = (await s.execute(
        select(col, Submission.review_status, func.count())
        .join(R, R.id == Submission.root_id)
        .where(Submission.company_id == ctx.company.id, Submission.is_latest,
               R.accepted_at_server >= ctx.start, R.accepted_at_server < ctx.end)
        .group_by(col, Submission.review_status))).all()
    out: dict = {}
    for key, status, n in rows:
        out.setdefault(key, {})[status] = n
    return out


async def _first_reports(s: AsyncSession, ctx: Ctx, group_col, start, end):
    col = getattr(Submission, group_col)
    return {k: (n, actives, last) for k, n, actives, last in (await s.execute(
        select(col, func.count(), func.count(func.distinct(Submission.user_id)), func.max(Submission.accepted_at_server))
        .where(Submission.company_id == ctx.company.id, Submission.revision == 1,
               Submission.accepted_at_server >= start, Submission.accepted_at_server < end)
        .group_by(col))).all()}


async def _decisions(s: AsyncSession, ctx: Ctx, group_col):
    col = getattr(Submission, group_col)
    out: dict = {}
    for key, decision, n in (await s.execute(
        select(col, SubmissionReview.decision, func.count())
        .join(Submission, Submission.id == SubmissionReview.submission_id)
        .where(SubmissionReview.company_id == ctx.company.id, SubmissionReview.decision.in_(("approved", "rejected")),
               SubmissionReview.created_at >= ctx.start, SubmissionReview.created_at < ctx.end)
        .group_by(col, SubmissionReview.decision))).all():
        out.setdefault(key, {})[decision] = n
    return out


async def _targets(s: AsyncSession, ctx: Ctx, scope: str) -> dict:
    if not ctx.target_period:
        return {}
    col = ReportTarget.branch_id if scope == "branch" else ReportTarget.user_id
    return dict((await s.execute(select(col, ReportTarget.target).where(
        ReportTarget.company_id == ctx.company.id, ReportTarget.scope == scope,
        ReportTarget.period == ctx.target_period))).all())


def _metrics(reports, actives, st, dec, target, prev_reports) -> dict:
    approved, rejected, pending = st.get("approved", 0), st.get("rejected", 0), st.get("pending", 0)
    d_ok, d_no = dec.get("approved", 0), dec.get("rejected", 0)
    return {
        "reports": reports, "active_agents": actives, "pending": pending, "approved": approved, "needs_correction": rejected,
        "target": target, "achievement": _pct(reports, target) if target else None,
        "reviewed_decisions": d_ok + d_no, "rejection_rate": _pct(d_no, d_ok + d_no),
        "previous_reports": prev_reports, "trend_pct": _trend(reports, prev_reports),
    }


@router.get("/overview")
async def overview(period: Period = "month", date_from: date | None = None, date_to: date | None = None,
                   admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    ctx = Ctx(await s.get(Company, admin.company_id), period, date_from, date_to)
    branches = (await s.execute(select(Branch).where(Branch.company_id == ctx.company.id, Branch.status == "active")
                                .order_by(Branch.name))).scalars().all()
    assigned = await _agents_by_branch(s, ctx.company.id)
    cur = await _first_reports(s, ctx, "branch_id", ctx.start, ctx.end)
    prev = await _first_reports(s, ctx, "branch_id", ctx.prev_start, ctx.prev_end)
    st = await _status_counts(s, ctx, "branch_id")
    dec = await _decisions(s, ctx, "branch_id")
    targets = await _targets(s, ctx, "branch")

    rows, totals = [], {"reports": 0, "pending": 0, "approved": 0, "needs_correction": 0, "d_ok": 0, "d_no": 0, "prev": 0, "target": 0}
    for b in branches:
        n, actives, _ = cur.get(b.id, (0, 0, None))
        m = _metrics(n, actives, st.get(b.id, {}), dec.get(b.id, {}), targets.get(b.id), prev.get(b.id, (0, 0, None))[0])
        rows.append({"branch_id": str(b.id), "name": b.name, "code": b.code, "assigned_agents": len(assigned.get(b.id, ())), **m})
    # company totals include every report, also ones without a branch or on a since-deactivated branch
    totals["reports"] = sum(v[0] for v in cur.values())
    totals["prev"] = sum(v[0] for v in prev.values())
    for d in st.values():
        totals["pending"] += d.get("pending", 0); totals["approved"] += d.get("approved", 0); totals["needs_correction"] += d.get("rejected", 0)
    for d in dec.values():
        totals["d_ok"] += d.get("approved", 0); totals["d_no"] += d.get("rejected", 0)
    company_actives = (await s.execute(select(func.count(func.distinct(Submission.user_id))).where(
        Submission.company_id == ctx.company.id, Submission.revision == 1,
        Submission.accepted_at_server >= ctx.start, Submission.accepted_at_server < ctx.end))).scalar_one()
    all_agents = {u for v in assigned.values() for u in v}

    # meetings by type of person, from the newest version of reports first submitted in the period
    R = aliased(Submission)
    types = (await s.execute(
        select(SubmissionPersonType.label_snapshot, func.count())
        .join(Submission, Submission.id == SubmissionPersonType.submission_id)
        .join(R, R.id == Submission.root_id)
        .where(SubmissionPersonType.company_id == ctx.company.id, Submission.is_latest,
               R.accepted_at_server >= ctx.start, R.accepted_at_server < ctx.end)
        .group_by(SubmissionPersonType.label_snapshot).order_by(func.count().desc()))).all()
    return {
        "period": ctx.meta(),
        "totals": {
            "reports": totals["reports"], "pending": totals["pending"], "approved": totals["approved"],
            "needs_correction": totals["needs_correction"], "assigned_agents": len(all_agents), "active_agents": company_actives,
            "reviewed_decisions": totals["d_ok"] + totals["d_no"], "rejection_rate": _pct(totals["d_no"], totals["d_ok"] + totals["d_no"]),
            "previous_reports": totals["prev"], "trend_pct": _trend(totals["reports"], totals["prev"]),
        },
        "branches": rows,
        "person_types": [{"label": label, "meetings": n} for label, n in types],
    }


@router.get("/branches/{branch_id}/agents")
async def branch_agents(branch_id: uuid.UUID, period: Period = "month", date_from: date | None = None, date_to: date | None = None,
                        admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    ctx = Ctx(await s.get(Company, admin.company_id), period, date_from, date_to)
    branch = await s.get(Branch, branch_id)
    if not branch or branch.company_id != ctx.company.id:
        raise HTTPException(404, "Not found")
    ids = (await _agents_by_branch(s, ctx.company.id)).get(branch_id, set())
    # agents who reported for this branch in the period count even if they have since moved
    cur_q = select(Submission.user_id, func.count(), func.max(Submission.accepted_at_server)).where(
        Submission.company_id == ctx.company.id, Submission.branch_id == branch_id, Submission.revision == 1,
        Submission.accepted_at_server >= ctx.start, Submission.accepted_at_server < ctx.end).group_by(Submission.user_id)
    cur = {u: (n, last) for u, n, last in (await s.execute(cur_q)).all()}
    prev = dict((await s.execute(
        select(Submission.user_id, func.count()).where(
            Submission.company_id == ctx.company.id, Submission.branch_id == branch_id, Submission.revision == 1,
            Submission.accepted_at_server >= ctx.prev_start, Submission.accepted_at_server < ctx.prev_end)
        .group_by(Submission.user_id))).all())
    R = aliased(Submission)
    st: dict = {}
    for uid, status, n in (await s.execute(
        select(Submission.user_id, Submission.review_status, func.count()).join(R, R.id == Submission.root_id)
        .where(Submission.company_id == ctx.company.id, Submission.branch_id == branch_id, Submission.is_latest,
               R.accepted_at_server >= ctx.start, R.accepted_at_server < ctx.end)
        .group_by(Submission.user_id, Submission.review_status))).all():
        st.setdefault(uid, {})[status] = n
    dec: dict = {}
    for uid, decision, n in (await s.execute(
        select(Submission.user_id, SubmissionReview.decision, func.count())
        .join(Submission, Submission.id == SubmissionReview.submission_id)
        .where(SubmissionReview.company_id == ctx.company.id, Submission.branch_id == branch_id,
               SubmissionReview.decision.in_(("approved", "rejected")),
               SubmissionReview.created_at >= ctx.start, SubmissionReview.created_at < ctx.end)
        .group_by(Submission.user_id, SubmissionReview.decision))).all():
        dec.setdefault(uid, {})[decision] = n
    targets = await _targets(s, ctx, "agent")
    users = {u.id: u for u in (await s.execute(select(User).where(User.id.in_(list(ids | set(cur)))))).scalars().all()} if (ids or cur) else {}
    last_any = dict((await s.execute(select(Submission.user_id, func.max(Submission.accepted_at_server))
                                     .where(Submission.company_id == ctx.company.id, Submission.user_id.in_(list(users)))
                                     .group_by(Submission.user_id))).all()) if users else {}
    rows = []
    for uid, u in users.items():
        n, _ = cur.get(uid, (0, None))
        m = _metrics(n, 1 if n else 0, st.get(uid, {}), dec.get(uid, {}), targets.get(uid), prev.get(uid, 0))
        rows.append({"agent_id": str(uid), "name": u.full_name, "employee_code": u.employee_code, "status": u.status,
                     "last_report_at": last_any.get(uid), **m})
    rows.sort(key=lambda r: (-r["reports"], r["name"]))
    return {"period": ctx.meta(), "branch": {"id": str(branch.id), "name": branch.name}, "agents": rows,
            "note": "A low count can also mean reports are still waiting to sync on the agent's phone. Check with the agent before judging."}


class TargetIn(BaseModel):
    scope: Literal["branch", "agent"]
    id: uuid.UUID
    period: Literal["weekly", "monthly"]
    target: int | None = Field(None, ge=0, le=100000)  # null removes the target


@router.put("/targets")
async def set_target(body: TargetIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    if body.scope == "branch":
        obj = await s.get(Branch, body.id)
    else:
        obj = await s.get(User, body.id)
        if obj and obj.role != "agent":
            obj = None
    if not obj or obj.company_id != admin.company_id:
        raise HTTPException(404, "Not found")
    col = ReportTarget.branch_id if body.scope == "branch" else ReportTarget.user_id
    row = (await s.execute(select(ReportTarget).where(ReportTarget.company_id == admin.company_id, ReportTarget.scope == body.scope,
                                                      col == body.id, ReportTarget.period == body.period))).scalar_one_or_none()
    if body.target is None:
        if row:
            await s.delete(row)
    elif row:
        row.target = body.target
    else:
        s.add(ReportTarget(company_id=admin.company_id, scope=body.scope, period=body.period, target=body.target,
                           branch_id=body.id if body.scope == "branch" else None, user_id=body.id if body.scope == "agent" else None))
    audit(s, admin, "target.set", body.scope, body.id)
    await s.commit()
    return {"scope": body.scope, "id": str(body.id), "period": body.period, "target": body.target}
