"""Dashboards, daily compliance (4.5), the Takeoff export (10), the field map, and call-centre performance."""
import csv
import io
import uuid
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.db import get_session
from app.models import Attendance, AuditLog, Branch, CallAttempt, Company, Region, SankalpEntry, User
from app.services.periods import period_bounds, tz_of
from app.services.sankalp import rules as R
from app.services.sankalp.ops import company_today
from app.services.scope import entry_scope, user_scope
from app.services.settings import load_settings, load_settings_on

router = APIRouter(tags=["reports"])
# How the dashboard counts an entry that is never called (5.1); the web shows the same words.
NOT_CALLED_EXISTING = "Not called (existing customer / applicant)"
RAG_EXPR = func.coalesce(SankalpEntry.rag_override, SankalpEntry.rag)


async def _days(s: AsyncSession, user: User, period: str, date_from: date | None, date_to: date | None) -> tuple[date, date]:
    company = await s.get(Company, user.company_id)
    _, _, first, last = period_bounds(period, tz_of(company.timezone), date_from, date_to)
    return first, last


def _csv(name: str, header: list[str], rows) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---------------------------------------------------------------- dashboard
@router.get("/dashboard")
async def dashboard(period: str = "today", date_from: date | None = None, date_to: date | None = None,
                    user: User = Depends(require_perm("dashboard.read")), s: AsyncSession = Depends(get_session)):
    """Entries counted on their count date, in the signed-in user's scope."""
    first, last = await _days(s, user, period, date_from, date_to)
    scope = await entry_scope(s, user)
    in_period = [scope, SankalpEntry.count_date >= first, SankalpEntry.count_date <= last]
    totals = (await s.execute(select(
        func.count(),
        func.count().filter(SankalpEntry.category.in_(R.LEAD_CATEGORIES)),
        func.count().filter(SankalpEntry.call_group == "dsa_cp"),
        func.count().filter(SankalpEntry.customer_validated),
        func.count().filter(SankalpEntry.lead_outcome == R.LOGGED_IN),
        func.count().filter(SankalpEntry.sankalp_success),
        func.count().filter(SankalpEntry.selection_status == R.ALLOCATE, SankalpEntry.status.is_(None)),
        func.count().filter(SankalpEntry.so_action.is_not(None)),
        func.count(func.distinct(SankalpEntry.so_user_id)),
    ).where(*in_period))).one()
    rag = dict((await s.execute(select(RAG_EXPR, func.count()).where(*in_period).group_by(RAG_EXPR))).all())
    by_cat = dict((await s.execute(select(SankalpEntry.category, func.count()).where(*in_period)
                                   .group_by(SankalpEntry.category))).all())
    # Existing Customer / Applicant entries are never selected (5.1): not "Pending"
    st = func.coalesce(SankalpEntry.status, SankalpEntry.selection_status,
                       case((SankalpEntry.call_group == "none", literal_column(f"'{NOT_CALLED_EXISTING}'")),
                            else_=literal_column("'Pending'")))
    by_status = dict((await s.execute(select(st, func.count()).where(*in_period).group_by(st))).all())
    trend = (await s.execute(select(SankalpEntry.count_date, func.count()).where(*in_period)
                             .group_by(SankalpEntry.count_date).order_by(SankalpEntry.count_date))).all()
    branches = (await s.execute(
        select(Branch.id, Branch.name, Region.name, func.count(),
               func.count().filter(SankalpEntry.category.in_(R.LEAD_CATEGORIES)),
               func.count().filter(SankalpEntry.customer_validated),
               func.count().filter(SankalpEntry.lead_outcome == R.LOGGED_IN),
               func.count().filter(RAG_EXPR == "RED"), func.count().filter(RAG_EXPR == "AMBER"),
               func.count().filter(RAG_EXPR == "GREEN"), func.count(func.distinct(SankalpEntry.so_user_id)))
        .join(Branch, Branch.id == SankalpEntry.branch_id).outerjoin(Region, Region.id == Branch.region_id)
        .where(*in_period).group_by(Branch.id, Branch.name, Region.name).order_by(func.count().desc()))).all()
    keys = ["entries", "lead_prospect", "dsa_cp", "validated", "logged_in", "sankalp_success", "awaiting_call",
            "open_so_actions", "active_sos"]
    return {
        "period": {"from": first, "to": last}, "totals": dict(zip(keys, totals)), "rag": rag,
        "by_category": {R.CATEGORIES.get(k, k): v for k, v in by_cat.items()}, "by_status": by_status,
        "trend": [{"day": d, "entries": n} for d, n in trend],
        "branches": [{"branch_id": str(b), "branch": n, "region": rn, "entries": t, "lead_prospect": lp, "validated": v,
                      "logged_in": li, "red": rd, "amber": am, "green": gr, "sos": so}
                     for b, n, rn, t, lp, v, li, rd, am, gr, so in branches],
    }


# ---------------------------------------------------------------- 4.5 daily compliance
async def compliance_rows(s: AsyncSession, user: User, day: date, branch_id: uuid.UUID | None = None,
                          region_id: uuid.UUID | None = None, q_text: str | None = None) -> dict:
    cfg = await load_settings_on(s, user.company_id, day)  # the targets that applied on that day
    q = (select(User, Branch.name, Region.name).outerjoin(Branch, Branch.id == User.branch_id)
         .outerjoin(Region, Region.id == Branch.region_id)
         .where(await user_scope(s, user), User.role == "sales_officer").order_by(Branch.name, User.full_name))
    if branch_id:
        q = q.where(User.branch_id == branch_id)
    if region_id:
        q = q.where(Branch.region_id == region_id)
    if q_text and q_text.strip():
        like = f"%{q_text.strip()}%"
        q = q.where(User.full_name.ilike(like) | User.employee_code.ilike(like))
    people = (await s.execute(q)).all()
    ids = [u.id for u, _, _ in people]
    counts = {uid: (n, lp) for uid, n, lp in (await s.execute(
        select(SankalpEntry.so_user_id, func.count(),
               func.count().filter(SankalpEntry.category.in_(R.LEAD_CATEGORIES),
                                   SankalpEntry.selection_status.notin_([R.NC_REPEAT, R.NC_DUPLICATE])
                                   | SankalpEntry.selection_status.is_(None)))
        .where(SankalpEntry.so_user_id.in_(ids or [uuid.uuid4()]), SankalpEntry.count_date == day)
        .group_by(SankalpEntry.so_user_id))).all()}
    marks = dict((await s.execute(select(Attendance.user_id, Attendance.code).where(
        Attendance.user_id.in_(ids or [uuid.uuid4()]), Attendance.day == day))).all())
    present_codes = {c.upper().replace(" ", "") for c in cfg.present_codes}
    rows, summary = [], defaultdict(int)
    for u, branch, region in people:
        if u.exit_date and u.exit_date < day:
            continue  # exits are excluded after the exit date
        n, lp = counts.get(u.id, (0, 0))
        code = marks.get(u.id)
        if u.joining_date and day < u.joining_date:
            state = "N/A"  # joiners: not counted before their joining date
        elif code is None:
            state = "no attendance"
        else:
            state = "present" if code.upper().replace(" ", "") in present_codes else "absent"
        shortfall = None if state in ("N/A",) else ("AB" if state == "absent" else max(cfg.daily_entry_target - n, 0))
        lead_short = None if state in ("N/A", "absent") else max(cfg.daily_lead_target - lp, 0)
        counted = state not in ("absent", "N/A")
        rows.append({"so_user_id": str(u.id), "emp_code": u.employee_code, "name": u.full_name, "designation": u.designation,
                     "branch": branch, "region": region, "attendance": code, "state": state, "entries": n,
                     "lead_prospect": lp, "shortfall": shortfall, "lead_shortfall": lead_short,
                     "met_target": counted and n >= cfg.daily_entry_target,
                     "met_lead_target": counted and lp >= cfg.daily_lead_target})
        summary["sos"] += 1
        summary["entries"] += n
        summary[state] += 1
        summary["met_target"] += rows[-1]["met_target"]
        summary["met_lead_target"] += rows[-1]["met_lead_target"]
        summary["expected"] += counted
    return {"day": day, "entry_target": cfg.daily_entry_target, "lead_target": cfg.daily_lead_target,
            "summary": dict(summary), "items": rows}


@router.get("/compliance")
async def compliance(day: date | None = None, branch_id: uuid.UUID | None = None, region_id: uuid.UUID | None = None,
                     q: str | None = None, user: User = Depends(require_perm("compliance.read")),
                     s: AsyncSession = Depends(get_session)):
    """Target 10 entries per present SO per day (all categories), 5 genuine Lead/Prospect; "AB" when absent."""
    return await compliance_rows(s, user, day or await company_today(s, user.company_id), branch_id, region_id, q)


@router.get("/compliance/export.csv")
async def compliance_csv(date_from: date, date_to: date, branch_id: uuid.UUID | None = None,
                         region_id: uuid.UUID | None = None, user: User = Depends(require_perm("compliance.export")),
                         s: AsyncSession = Depends(get_session)):
    if date_to < date_from or (date_to - date_from).days > 62:
        raise HTTPException(422, "Choose up to 62 days")
    states = {"present": "Present", "absent": "Absent", "N/A": "Not joined yet", "no attendance": "Not marked"}
    yn = lambda b: "Y" if b else "N"  # noqa: E731
    out = []
    d = date_from
    while d <= date_to:
        data = await compliance_rows(s, user, d, branch_id, region_id)
        for r in data["items"]:
            na = r["state"] == "N/A"
            out.append([d, r["emp_code"], r["name"], r["designation"], r["region"] or "", r["branch"] or "",
                        r["attendance"] or "", states.get(r["state"], r["state"]), r["entries"], r["lead_prospect"],
                        data["entry_target"], data["lead_target"],
                        r["shortfall"] if r["shortfall"] is not None else "N/A",
                        "N/A" if na else ("AB" if r["state"] == "absent" else r["lead_shortfall"]),
                        "N/A" if na else yn(r["met_target"]), "N/A" if na else yn(r["met_lead_target"])])
        d += timedelta(days=1)
    return _csv(f"sankalp_compliance_{date_from}_{date_to}.csv",
                ["Date", "Emp ID", "Name", "Designation", "Region", "Branch", "Attendance", "Day", "Entries",
                 "Lead/Prospect (genuine)", "Entry target", "Lead/Prospect target", "Shortfall", "Lead/Prospect shortfall",
                 "Met entry target", "Met Lead/Prospect target"], out)


# ---------------------------------------------------------------- 10 Takeoff export
@router.get("/takeoff/export.csv")
async def takeoff_csv(date_from: date, date_to: date, user: User = Depends(require_perm("takeoff.export")),
                      s: AsyncSession = Depends(get_session)):
    """The flags the incentive needs (section 10). The money is calculated outside the app."""
    rows = (await s.execute(
        select(SankalpEntry, User.employee_code, User.full_name, Branch.name, Region.name)
        .join(User, User.id == SankalpEntry.so_user_id).join(Branch, Branch.id == SankalpEntry.branch_id)
        .outerjoin(Region, Region.id == Branch.region_id)
        .where(SankalpEntry.company_id == user.company_id, SankalpEntry.entry_date >= date_from,
               SankalpEntry.entry_date <= date_to).order_by(SankalpEntry.entry_date, SankalpEntry.entry_code))).all()
    yn = lambda b: "Y" if b else "N"  # noqa: E731
    return _csv(f"sankalp_takeoff_{date_from}_{date_to}.csv",
                ["Entry ID", "Emp ID (credited SO)", "SO name", "Branch", "Region", "Entry date", "Count date", "Category",
                 "Phone", "Selection", "Status", "RAG", "Repeat entry by same SO", "Customer validated",
                 "First validation for this number", "Validated on", "Lead outcome", "TCS ID", "Login date",
                 "Counts as Sankalp success"],
                [[e.entry_code, code, name, b, r, e.entry_date, e.count_date, R.CATEGORIES.get(e.category), e.phone,
                  e.selection_status or "", e.status or "", e.rag_override or e.rag, yn(e.selection_status == R.NC_REPEAT),
                  yn(e.customer_validated), yn(e.first_validation), e.validated_on or "", e.lead_outcome or "",
                  e.tcs_id or "", e.login_date or "", yn(e.sankalp_success)] for e, code, name, b, r in rows])


# ---------------------------------------------------------------- field map
MAP_LIMIT = 3000

@router.get("/map/entries")
async def map_entries(period: str = "today", date_from: date | None = None, date_to: date | None = None,
                      branch_id: uuid.UUID | None = None, so_user_id: uuid.UUID | None = None,
                      user: User = Depends(require_perm("map.read")), s: AsyncSession = Depends(get_session)):
    """Where entries were made (the GPS fix at Submit). Recorded positions, not live tracking."""
    first, last = await _days(s, user, period, date_from, date_to)
    q = (select(SankalpEntry, User.full_name, Branch.name).join(User, User.id == SankalpEntry.so_user_id)
         .join(Branch, Branch.id == SankalpEntry.branch_id)
         .where(await entry_scope(s, user), SankalpEntry.entry_date >= first, SankalpEntry.entry_date <= last))
    if branch_id:
        q = q.where(SankalpEntry.branch_id == branch_id)
    if so_user_id:
        q = q.where(SankalpEntry.so_user_id == so_user_id)
    total = (await s.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await s.execute(q.order_by(SankalpEntry.submitted_at_device.desc()).limit(MAP_LIMIT))).all()
    with_loc = [r for r in rows if r[0].latitude is not None]
    return {
        # the map draws at most MAP_LIMIT points; the screen says so when the period has more (no silent cut)
        "period": {"from": first, "to": last}, "total": total, "shown": len(rows), "capped": total > len(rows),
        "limit": MAP_LIMIT, "without_location": len(rows) - len(with_loc),
        "markers": [{"id": str(e.id), "entry_code": e.entry_code, "lat": float(e.latitude), "lng": float(e.longitude),
                     "accuracy_m": float(e.accuracy_m) if e.accuracy_m is not None else None, "so_name": so,
                     "branch": b, "category": R.CATEGORIES.get(e.category), "person_name": e.person_name,
                     "rag": e.rag_override or e.rag, "submitted_at_device": e.submitted_at_device,
                     "place_name": e.place_name} for e, so, b in with_loc],
    }


# ---------------------------------------------------------------- call-centre performance
@router.get("/reports/callcentre")
async def callcentre_report(period: str = "today", date_from: date | None = None, date_to: date | None = None,
                            user: User = Depends(require_perm("calls.manage")), s: AsyncSession = Depends(get_session)):
    first, last = await _days(s, user, period, date_from, date_to)
    rows = (await s.execute(
        select(User.id, User.full_name, func.count(CallAttempt.id),
               func.count().filter(CallAttempt.outcome == R.CONNECTED),
               func.count().filter(CallAttempt.outcome.in_(R.UNANSWERED)),
               func.count().filter(CallAttempt.row_status.like("Validated%")),
               func.count(func.distinct(CallAttempt.entry_id)))
        .join(CallAttempt, CallAttempt.caller_id == User.id)
        .where(User.company_id == user.company_id, CallAttempt.call_date >= first, CallAttempt.call_date <= last)
        .group_by(User.id, User.full_name).order_by(User.full_name))).all()
    # first attempt within the target (setting: 1 day) of the entry date
    cfg = await load_settings(s, user.company_id)
    firsts = (select(CallAttempt.entry_id, func.min(CallAttempt.call_date).label("first")).group_by(CallAttempt.entry_id)
              .subquery())
    tat = (await s.execute(select(
        func.count(), func.count().filter(firsts.c.first - SankalpEntry.entry_date <= cfg.first_attempt_target_days))
        .select_from(firsts).join(SankalpEntry, SankalpEntry.id == firsts.c.entry_id)
        .where(SankalpEntry.company_id == user.company_id, firsts.c.first >= first, firsts.c.first <= last))).one()
    return {"period": {"from": first, "to": last},
            "first_attempts": tat[0], "first_attempt_on_time": tat[1], "target_days": cfg.first_attempt_target_days,
            "callers": [{"caller_id": str(i), "name": n, "attempts": a, "connected": c, "unanswered": u, "validated": v,
                         "entries": en} for i, n, a, c, u, v, en in rows]}



# ---------------------------------------------------------------- audit log
@router.get("/audit-logs")
async def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                     user: User = Depends(require_perm("audit.read")), s: AsyncSession = Depends(get_session)):
    total = (await s.execute(select(func.count()).select_from(AuditLog).where(AuditLog.company_id == user.company_id))).scalar_one()
    rows = (await s.execute(
        select(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.actor_id)
        .where(AuditLog.company_id == user.company_id)
        .order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [{"id": str(a.id), "actor": name, "action": a.action, "entity_type": a.entity_type,
                       "entity_id": a.entity_id, "details": a.details, "created_at": a.created_at} for a, name in rows],
            "total": total, "page": page, "page_size": page_size}