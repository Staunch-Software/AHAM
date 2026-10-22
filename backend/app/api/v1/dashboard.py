from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.api.v1.submissions import _base_query, _row
from app.core.db import get_session
from app.models import AuditLog, Branch, Company, Submission, User
from app.services.periods import period_bounds, tz_of

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    cid = admin.company_id
    company = await s.get(Company, cid)
    tz = tz_of(company.timezone)
    today_start, _, _, _ = period_bounds("today", tz)

    async def count(q):
        return (await s.execute(q)).scalar_one()

    agents = await count(select(func.count()).select_from(User).where(
        User.company_id == cid, User.role == "agent", User.status == "active"))
    branches = await count(select(func.count()).select_from(Branch).where(
        Branch.company_id == cid, Branch.status == "active"))
    today_n = await count(select(func.count()).select_from(Submission).where(
        Submission.company_id == cid, Submission.revision == 1, Submission.accepted_at_server >= today_start))
    # review queue = the newest version of each report; superseded versions are history
    pending = await count(select(func.count()).select_from(Submission).where(
        Submission.company_id == cid, Submission.is_latest, Submission.review_status == "pending"))
    needs_fix = await count(select(func.count()).select_from(Submission).where(
        Submission.company_id == cid, Submission.is_latest, Submission.review_status == "rejected"))
    day = cast(func.timezone(company.timezone, Submission.accepted_at_server), Date)
    trend = (await s.execute(
        select(day, func.count()).where(Submission.company_id == cid, Submission.revision == 1,
                                        Submission.accepted_at_server >= today_start - timedelta(days=13))
        .group_by(day).order_by(day))).all()
    recent = (await s.execute(
        _base_query().where(Submission.company_id == cid, Submission.is_latest)
        .order_by(Submission.accepted_at_server.desc()).limit(5))).all()
    return {
        "total_agents": agents, "active_branches": branches, "submissions_today": today_n,
        "pending_review": pending, "needs_correction": needs_fix,
        "recent": [_row(*r) for r in recent],
        "trend": [{"date": d.isoformat(), "count": n} for d, n in trend],
    }


@router.get("/audit-logs")
async def audit_logs(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session),
):
    base = select(AuditLog).where(AuditLog.company_id == admin.company_id)
    total = (await s.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await s.execute(
        select(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.actor_id)
        .where(AuditLog.company_id == admin.company_id)
        .order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [{"id": str(a.id), "actor": name, "action": a.action, "entity_type": a.entity_type,
                   "entity_id": a.entity_id, "created_at": a.created_at} for a, name in rows],
        "total": total, "page": page, "page_size": page_size,
    }
