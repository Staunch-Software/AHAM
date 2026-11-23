"""Dashboards, daily compliance (4.5), the Takeoff export (10), the field map, and call-centre performance."""
import csv
import io
import uuid
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.db import get_session
from app.models import (
    Attendance,
    AuditLog,
    Branch,
    CallAllocation,
    CallAttempt,
    CallerAbsence,
    Company,
    Region,
    SankalpEntry,
    User,
)
from app.services.periods import period_bounds, tz_of
from app.services.sankalp import rules as R
from app.services.sankalp.ops import company_today
from app.services.sankalp.views import current_status
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
                    conv_from: date | None = None, conv_to: date | None = None,
                    user: User = Depends(require_perm("dashboard.read")), s: AsyncSession = Depends(get_session)):
    """Entries counted on their count date, in the signed-in user's scope. The lead conversion has its own range of
    entry dates (conv_from / conv_to): by default every entry from Takeoff start to today."""
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
    # Sankalp lead conversion by region, as the Takeoff master: every entry since Takeoff start in the user's scope
    # (not the period picked, since a lead logs in weeks after it was entered). Validated lead-type entries, and how
    # many of them are the Sankalp success (logged in), were rejected, or are still open.
    takeoff_start = (await load_settings(s, user.company_id)).takeoff_start
    conv_first = max(conv_from or takeoff_start, takeoff_start)  # a Takeoff lead is never older than Takeoff start
    conv_last = conv_to or await company_today(s, user.company_id)
    lead_type = or_(SankalpEntry.call_group == "lead", SankalpEntry.status == R.VALIDATED_CONVERTED,
                    SankalpEntry.lead_outcome.is_not(None))
    conversion = (await s.execute(
        select(Region.name, func.count(), func.count().filter(SankalpEntry.sankalp_success),
               func.count().filter(SankalpEntry.lead_outcome == R.OUTCOME_REJECTED))
        .join(Branch, Branch.id == SankalpEntry.branch_id).outerjoin(Region, Region.id == Branch.region_id)
        .where(scope, SankalpEntry.entry_date >= conv_first, SankalpEntry.entry_date <= conv_last,
               SankalpEntry.customer_validated, lead_type)
        .group_by(Region.name).order_by(Region.name))).all()
    conv_rows = [{"region": rn, "validated": n, "logged_in": li, "rejected": rj, "open": n - li - rj}
                 for rn, n, li, rj in conversion]
    keys = ["entries", "lead_prospect", "dsa_cp", "validated", "logged_in", "sankalp_success", "awaiting_call",
            "open_so_actions", "active_sos"]
    return {
        "period": {"from": first, "to": last}, "totals": dict(zip(keys, totals)), "rag": rag,
        "by_category": {R.CATEGORIES.get(k, k): v for k, v in by_cat.items()}, "by_status": by_status,
        "trend": [{"day": d, "entries": n} for d, n in trend],
        "branches": [{"branch_id": str(b), "branch": n, "region": rn, "entries": t, "lead_prospect": lp, "validated": v,
                      "logged_in": li, "red": rd, "amber": am, "green": gr, "sos": so}
                     for b, n, rn, t, lp, v, li, rd, am, gr, so in branches],
        "conversion": {"since": takeoff_start, "from": conv_first, "to": conv_last, "regions": conv_rows,
                       "total": {k: sum(r[k] for r in conv_rows) for k in ("validated", "logged_in", "rejected", "open")}},
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
            state = "absent" if cfg.unmarked_attendance == "absent" else "no attendance"
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
                 "Mobile number", "Current status", "RAG", "Repeat entry by same SO", "Customer validated",
                 "First validation for this number", "Validated on", "Lead outcome", "TCS ID", "Login date",
                 "Counts as Sankalp success"],
                [[e.entry_code, code, name, b, r, e.entry_date, e.count_date, R.CATEGORIES.get(e.category), e.phone,
                  current_status(e), R.RAG_LABELS.get(e.rag_override or e.rag), yn(e.selection_status == R.NC_REPEAT),
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
    # first try on time, as the Takeoff master: of the validated entries, those first called within the target
    # (setting: 1 day) of the entry date
    cfg = await load_settings(s, user.company_id)
    firsts = (select(CallAttempt.entry_id, func.min(CallAttempt.call_date).label("first")).group_by(CallAttempt.entry_id)
              .subquery())
    tat = (await s.execute(select(
        func.count(), func.count().filter(firsts.c.first - SankalpEntry.entry_date <= cfg.first_attempt_target_days))
        .select_from(firsts).join(SankalpEntry, SankalpEntry.id == firsts.c.entry_id)
        .where(SankalpEntry.company_id == user.company_id, SankalpEntry.customer_validated,
               firsts.c.first >= first, firsts.c.first <= last))).one()
    return {"period": {"from": first, "to": last},
            "first_attempts": tat[0], "first_attempt_on_time": tat[1], "target_days": cfg.first_attempt_target_days,
            "callers": [{"caller_id": str(i), "name": n, "attempts": a, "connected": c, "unanswered": u, "validated": v,
                         "entries": en} for i, n, a, c, u, v, en in rows]}


@router.get("/reports/callcentre/caller/{caller_id}")
async def caller_analytics(
    caller_id: uuid.UUID,
    period: str = "today",
    date_from: date | None = None,
    date_to: date | None = None,
    user: User = Depends(require_perm("calls.manage")),
    s: AsyncSession = Depends(get_session),
):
    """Detailed analytics window for an individual caller: profile, workload, outcome mix, hourly efficiency, and call history."""
    caller = await s.get(User, caller_id)
    if not caller or caller.company_id != user.company_id:
        raise HTTPException(404, "Caller not found")

    today = await company_today(s, user.company_id)
    first, last = await _days(s, user, period, date_from, date_to)
    cfg = await load_settings(s, user.company_id)

    # Usual branches
    usual_branches = (await s.execute(
        select(Branch.name).where(Branch.usual_caller_id == caller_id, Branch.company_id == user.company_id)
        .order_by(Branch.name)
    )).scalars().all()

    # Is absent today
    absent_row = (await s.execute(
        select(CallerAbsence.id).where(
            CallerAbsence.caller_id == caller_id,
            CallerAbsence.day == today,
            CallerAbsence.company_id == user.company_id,
        )
    )).first()
    is_absent_today = absent_row is not None

    # Today's allocation load & calls made
    today_load = (await s.execute(
        select(func.count(CallAllocation.id)).where(
            CallAllocation.caller_id == caller_id,
            CallAllocation.run_date == today,
            CallAllocation.company_id == user.company_id,
        )
    )).scalar_one()

    today_calls_made = (await s.execute(
        select(func.count(CallAttempt.id)).where(
            CallAttempt.caller_id == caller_id,
            CallAttempt.call_date == today,
            CallAttempt.company_id == user.company_id,
        )
    )).scalar_one()

    daily_limit = getattr(cfg, "caller_daily_limit", None) or 250
    is_active = (getattr(caller, "status", "active") == "active") and (caller.exit_date is None or caller.exit_date >= today)

    # Summary metrics in period
    summary_row = (await s.execute(
        select(
            func.count(CallAttempt.id),
            func.count(func.distinct(CallAttempt.entry_id)),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
            func.count().filter(CallAttempt.outcome.in_(R.UNANSWERED)),
            func.count().filter(CallAttempt.row_status.like("Validated%")),
        ).where(
            CallAttempt.caller_id == caller_id,
            CallAttempt.company_id == user.company_id,
            CallAttempt.call_date >= first,
            CallAttempt.call_date <= last,
        )
    )).one()

    total_attempts, unique_entries, connected, unanswered, validated = summary_row
    connected_pct = round((connected / total_attempts * 100), 1) if total_attempts > 0 else 0.0
    unanswered_pct = round((unanswered / total_attempts * 100), 1) if total_attempts > 0 else 0.0
    conversion_pct = round((validated / unique_entries * 100), 1) if unique_entries > 0 else 0.0

    # First attempt TAT
    firsts = (
        select(CallAttempt.entry_id, func.min(CallAttempt.call_date).label("first"))
        .where(CallAttempt.caller_id == caller_id)
        .group_by(CallAttempt.entry_id)
        .subquery()
    )
    tat = (await s.execute(
        select(
            func.count(),
            func.count().filter(firsts.c.first - SankalpEntry.entry_date <= cfg.first_attempt_target_days),
        )
        .select_from(firsts)
        .join(SankalpEntry, SankalpEntry.id == firsts.c.entry_id)
        .where(
            SankalpEntry.company_id == user.company_id,
            SankalpEntry.customer_validated,
            firsts.c.first >= first,
            firsts.c.first <= last,
        )
    )).one()

    num_days = max((last - first).days + 1, 1)
    avg_calls_per_day = round(total_attempts / num_days, 1)

    # Outcome breakdown
    outcome_counts = (await s.execute(
        select(CallAttempt.outcome, func.count(CallAttempt.id))
        .where(
            CallAttempt.caller_id == caller_id,
            CallAttempt.company_id == user.company_id,
            CallAttempt.call_date >= first,
            CallAttempt.call_date <= last,
        )
        .group_by(CallAttempt.outcome)
        .order_by(func.count(CallAttempt.id).desc())
    )).all()

    outcomes_list = []
    for outc, cnt in outcome_counts:
        pct = round((cnt / total_attempts * 100), 1) if total_attempts > 0 else 0.0
        grp = "positive" if outc == R.CONNECTED else ("unanswered" if outc in R.UNANSWERED else "discarded")
        outcomes_list.append({"outcome": outc, "count": cnt, "pct": pct, "group": grp})

    # Slot distribution
    slot_counts = (await s.execute(
        select(
            CallAttempt.slot,
            func.count(CallAttempt.id),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
        )
        .where(
            CallAttempt.caller_id == caller_id,
            CallAttempt.company_id == user.company_id,
            CallAttempt.call_date >= first,
            CallAttempt.call_date <= last,
        )
        .group_by(CallAttempt.slot)
    )).all()
    slot_map = {s_name: (att, conn) for s_name, att, conn in slot_counts}
    slots_list = []
    for s_slot in R.SLOTS:
        s_att, s_conn = slot_map.get(s_slot, (0, 0))
        c_pct = round((s_conn / s_att * 100), 1) if s_att > 0 else 0.0
        slots_list.append({"slot": s_slot, "attempts": s_att, "connected": s_conn, "connect_pct": c_pct})

    # Category performance
    cat_counts = (await s.execute(
        select(
            SankalpEntry.category,
            func.count(func.distinct(CallAttempt.entry_id)),
            func.count(CallAttempt.id),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
            func.count().filter(CallAttempt.row_status.like("Validated%")),
        )
        .join(SankalpEntry, SankalpEntry.id == CallAttempt.entry_id)
        .where(
            CallAttempt.caller_id == caller_id,
            CallAttempt.company_id == user.company_id,
            CallAttempt.call_date >= first,
            CallAttempt.call_date <= last,
        )
        .group_by(SankalpEntry.category)
    )).all()

    category_list = []
    for cat_key, ent_cnt, att_cnt, conn_cnt, val_cnt in cat_counts:
        category_list.append({
            "category": cat_key,
            "label": R.CATEGORIES.get(cat_key, cat_key),
            "entries": ent_cnt,
            "attempts": att_cnt,
            "connected": conn_cnt,
            "validated": val_cnt,
            "connect_pct": round((conn_cnt / att_cnt * 100), 1) if att_cnt > 0 else 0.0,
        })

    # Recent 50 calls
    recent_rows = (await s.execute(
        select(
            CallAttempt.id,
            CallAttempt.call_date,
            CallAttempt.slot,
            CallAttempt.created_at,
            CallAttempt.outcome,
            CallAttempt.row_status,
            CallAttempt.cycle,
            SankalpEntry.id,
            SankalpEntry.entry_code,
            SankalpEntry.person_name,
            SankalpEntry.phone,
            SankalpEntry.category,
            Branch.name,
        )
        .join(SankalpEntry, SankalpEntry.id == CallAttempt.entry_id)
        .join(Branch, Branch.id == SankalpEntry.branch_id)
        .where(
            CallAttempt.caller_id == caller_id,
            CallAttempt.company_id == user.company_id,
        )
        .order_by(CallAttempt.created_at.desc())
        .limit(50)
    )).all()

    recent_calls = []
    for att_id, cdate, slot, cat_at, outc, rstat, cycle, eid, ecode, pname, phone, cat, bname in recent_rows:
        recent_calls.append({
            "id": str(att_id),
            "call_date": str(cdate),
            "slot": slot,
            "created_at": cat_at.isoformat() if cat_at else None,
            "outcome": outc,
            "row_status": rstat,
            "cycle": cycle,
            "entry_id": str(eid),
            "entry_code": ecode,
            "person_name": pname,
            "phone": phone,
            "category": R.CATEGORIES.get(cat, cat),
            "branch_name": bname,
        })

    return {
        "caller": {
            "id": str(caller.id),
            "name": caller.full_name,
            "employee_code": caller.employee_code,
            "languages": caller.languages or [],
            "usual_branches": usual_branches,
            "is_absent_today": is_absent_today,
            "active": is_active,
            "daily_limit": daily_limit,
            "today_load": today_load,
            "today_calls_made": today_calls_made,
        },
        "period": {
            "label": period,
            "from": str(first),
            "to": str(last),
        },
        "summary": {
            "total_attempts": total_attempts,
            "unique_entries": unique_entries,
            "connected_calls": connected,
            "connected_pct": connected_pct,
            "unanswered_calls": unanswered,
            "unanswered_pct": unanswered_pct,
            "validated_entries": validated,
            "conversion_pct": conversion_pct,
            "first_attempts_on_time": tat[1],
            "first_attempt_on_time_pct": round((tat[1] / tat[0] * 100), 1) if tat[0] > 0 else 0.0,
            "avg_calls_per_day": avg_calls_per_day,
        },
        "outcome_breakdown": outcomes_list,
        "slot_distribution": slots_list,
        "category_performance": category_list,
        "recent_calls": recent_calls,
    }


def _build_caller_analytics_workbook(data: dict) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Analytics Dashboard"
    ws.views.sheetView[0].showGridLines = True

    fill_navy = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    fill_subnavy = PatternFill(start_color="283079", end_color="283079", fill_type="solid")
    fill_card = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    font_banner = Font(name="Calibri", size=14, bold=True, color="1E1B4B")
    font_subbanner = Font(name="Calibri", size=11, color="64748B")
    font_section = Font(name="Calibri", size=12, bold=True, color="1E1B4B")
    font_white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_card_num = Font(name="Calibri", size=15, bold=True, color="1E1B4B")
    font_card_sub = Font(name="Calibri", size=10, bold=False, color="64748B")
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_data = Font(name="Calibri", size=11)

    thin = Side(border_style="thin", color="CBD5E1")
    box_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    caller = data["caller"]
    summary = data["summary"]
    period = data["period"]

    ws.cell(row=1, column=1, value="AHAM HOUSING FINANCE · CALL CENTRE CALLER ANALYTICS").font = font_banner
    ws.cell(
        row=2,
        column=1,
        value=f"Caller: {caller['name']} ({caller['employee_code']}) · Period: {period['from']} to {period['to']} ({period['label']})",
    ).font = font_subbanner

    cards = [
        ("TOTAL CALLS MADE", f"{summary['total_attempts']:,}", f"{summary['unique_entries']:,} Unique Customers", 1, 2),
        ("CONNECTED CALLS", f"{summary['connected_calls']:,}", f"{summary['connected_pct']}% Connect Rate", 3, 4),
        ("VALIDATED CONVERSIONS", f"{summary['validated_entries']:,}", f"{summary['conversion_pct']}% Conversion Rate", 5, 6),
        ("FIRST TRY ON-TIME", f"{summary['first_attempt_on_time_pct']}%", f"{summary['first_attempts_on_time']} Within TAT", 7, 8),
    ]
    for title, val, sub, c1, c2 in cards:
        ws.merge_cells(start_row=4, start_column=c1, end_row=4, end_column=c2)
        ws.merge_cells(start_row=5, start_column=c1, end_row=5, end_column=c2)
        ws.merge_cells(start_row=6, start_column=c1, end_row=6, end_column=c2)

        c_t = ws.cell(row=4, column=c1, value=title)
        c_t.font = font_subbanner
        c_t.alignment = Alignment(horizontal="center", vertical="center")

        c_v = ws.cell(row=5, column=c1, value=val)
        c_v.font = font_card_num
        c_v.alignment = Alignment(horizontal="center", vertical="center")

        c_s = ws.cell(row=6, column=c1, value=sub)
        c_s.font = font_card_sub
        c_s.alignment = Alignment(horizontal="center", vertical="center")

        for r in range(4, 7):
            for c in range(c1, c2 + 1):
                cell = ws.cell(row=r, column=c)
                cell.fill = fill_card
                cell.border = box_border

    ws.cell(row=8, column=1, value="Call Outcome Breakdown").font = font_section
    headers_outcome = ["Outcome", "Call Count", "Share (%)", "Classification"]
    for c_idx, h in enumerate(headers_outcome, start=1):
        cell = ws.cell(row=9, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    cur_row = 10
    for ob in data.get("outcome_breakdown", []):
        ws.cell(row=cur_row, column=1, value=ob["outcome"]).font = font_bold
        ws.cell(row=cur_row, column=2, value=ob["count"]).font = font_data
        ws.cell(row=cur_row, column=3, value=f"{ob['pct']}%").font = font_data
        ws.cell(row=cur_row, column=4, value=ob["group"].title()).font = font_data
        for c in range(1, 5):
            ws.cell(row=cur_row, column=c).border = box_border
        cur_row += 1

    ws.cell(row=8, column=6, value="Hourly Productivity Slots").font = font_section
    headers_slot = ["Slot", "Attempts", "Connected", "Connect (%)"]
    for c_idx, h in enumerate(headers_slot, start=6):
        cell = ws.cell(row=9, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_subnavy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    slot_row = 10
    for s_item in data.get("slot_distribution", []):
        ws.cell(row=slot_row, column=6, value=s_item["slot"]).font = font_bold
        ws.cell(row=slot_row, column=7, value=s_item["attempts"]).font = font_data
        ws.cell(row=slot_row, column=8, value=s_item["connected"]).font = font_data
        ws.cell(row=slot_row, column=9, value=f"{s_item['connect_pct']}%").font = font_data
        for c in range(6, 10):
            ws.cell(row=slot_row, column=c).border = box_border
        slot_row += 1

    cat_start = max(cur_row, slot_row) + 2
    ws.cell(row=cat_start, column=1, value="Product Category Performance").font = font_section
    headers_cat = ["Category", "Entries Called", "Attempts", "Connected", "Validated", "Connect (%)"]
    for c_idx, h in enumerate(headers_cat, start=1):
        cell = ws.cell(row=cat_start + 1, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    c_row = cat_start + 2
    for cat_item in data.get("category_performance", []):
        ws.cell(row=c_row, column=1, value=cat_item["label"]).font = font_bold
        ws.cell(row=c_row, column=2, value=cat_item["entries"]).font = font_data
        ws.cell(row=c_row, column=3, value=cat_item["attempts"]).font = font_data
        ws.cell(row=c_row, column=4, value=cat_item["connected"]).font = font_data
        ws.cell(row=c_row, column=5, value=cat_item["validated"]).font = font_data
        ws.cell(row=c_row, column=6, value=f"{cat_item.get('connect_pct', 0)}%").font = font_data
        for c in range(1, 7):
            ws.cell(row=c_row, column=c).border = box_border
        c_row += 1

    ws2 = wb.create_sheet(title="Call History Log")
    ws2.views.sheetView[0].showGridLines = True

    ws2.cell(row=1, column=1, value=f"CALL ACTIVITY HISTORY · {caller['name']}").font = font_banner
    ws2.cell(row=2, column=1, value=f"Last {len(data.get('recent_calls', []))} Call Attempts Recorded").font = font_subbanner

    headers_log = ["Call Date", "Slot", "Entry Code", "Customer Name", "Phone", "Category", "Branch", "Outcome", "Row Status"]
    for c_idx, h in enumerate(headers_log, start=1):
        cell = ws2.cell(row=4, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    l_row = 5
    for rc in data.get("recent_calls", []):
        ws2.cell(row=l_row, column=1, value=rc["call_date"]).font = font_data
        ws2.cell(row=l_row, column=2, value=rc["slot"]).font = font_data
        ws2.cell(row=l_row, column=3, value=rc["entry_code"]).font = font_bold
        ws2.cell(row=l_row, column=4, value=rc["person_name"]).font = font_data
        ws2.cell(row=l_row, column=5, value=rc["phone"]).font = font_data
        ws2.cell(row=l_row, column=6, value=rc["category"]).font = font_data
        ws2.cell(row=l_row, column=7, value=rc["branch_name"]).font = font_data
        ws2.cell(row=l_row, column=8, value=rc["outcome"]).font = font_bold
        ws2.cell(row=l_row, column=9, value=rc["row_status"] or "—").font = font_data
        for c in range(1, 10):
            ws2.cell(row=l_row, column=c).border = box_border
        l_row += 1

    for s_sheet in (ws, ws2):
        for col in s_sheet.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                val_str = str(cell.value or "")
                if "\n" in val_str:
                    val_str = max(val_str.split("\n"), key=len)
                if len(val_str) > max_len and cell.row > 2:
                    max_len = len(val_str)
            s_sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@router.get("/reports/callcentre/caller/{caller_id}/export.xlsx")
async def export_caller_analytics(
    caller_id: uuid.UUID,
    period: str = "today",
    date_from: date | None = None,
    date_to: date | None = None,
    user: User = Depends(require_perm("calls.manage")),
    s: AsyncSession = Depends(get_session),
):
    """Download comprehensive caller analytics report in Excel format (.xlsx) with KPI Dashboard and Call Log."""
    data = await caller_analytics(caller_id, period, date_from, date_to, user, s)
    buf = _build_caller_analytics_workbook(data)
    name = f"caller_analytics_{data['caller']['name'].replace(' ', '_')}_{period}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


# ---------------------------------------------------------------- master call-centre analytics & team report
@router.get("/reports/callcentre/master-analytics")
async def master_callcentre_analytics(
    period: str = "today",
    date_from: date | None = None,
    date_to: date | None = None,
    caller_id: uuid.UUID | None = None,
    user: User = Depends(require_perm("calls.manage")),
    s: AsyncSession = Depends(get_session),
):
    """Consolidated Call Centre Team Analytics: visual data analytics, timeline trend graphs, caller comparative rankings, outcome breakdown, and slot heatmaps."""
    first, last = await _days(s, user, period, date_from, date_to)
    today = await company_today(s, user.company_id)
    cfg = await load_settings(s, user.company_id)
    daily_limit = getattr(cfg, "caller_daily_limit", None) or 250

    # 1. Fetch all callers in the company
    callers_users = (await s.execute(
        select(User).where(User.company_id == user.company_id, User.role == "caller")
        .order_by(User.full_name)
    )).scalars().all()

    usual_branches_map = defaultdict(list)
    for bname, cid in (await s.execute(
        select(Branch.name, Branch.usual_caller_id).where(
            Branch.company_id == user.company_id, Branch.usual_caller_id.is_not(None)
        )
    )).all():
        usual_branches_map[cid].append(bname)

    absent_ids = set((await s.execute(
        select(CallerAbsence.caller_id).where(
            CallerAbsence.company_id == user.company_id, CallerAbsence.day == today
        )
    )).scalars().all())

    loads_today = dict((await s.execute(
        select(CallAllocation.caller_id, func.count(CallAllocation.id)).where(
            CallAllocation.company_id == user.company_id,
            CallAllocation.run_date == today,
            CallAllocation.caller_id.is_not(None),
        ).group_by(CallAllocation.caller_id)
    )).all())

    made_today = dict((await s.execute(
        select(CallAttempt.caller_id, func.count(CallAttempt.id)).where(
            CallAttempt.company_id == user.company_id,
            CallAttempt.call_date == today,
        ).group_by(CallAttempt.caller_id)
    )).all())

    # Build filter conditions
    filter_conds = [
        CallAttempt.company_id == user.company_id,
        CallAttempt.call_date >= first,
        CallAttempt.call_date <= last,
    ]
    if caller_id:
        filter_conds.append(CallAttempt.caller_id == caller_id)

    # 2. Team summary metrics in selected period
    summary_row = (await s.execute(
        select(
            func.count(CallAttempt.id),
            func.count(func.distinct(CallAttempt.entry_id)),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
            func.count().filter(CallAttempt.outcome.in_(R.UNANSWERED)),
            func.count().filter(CallAttempt.row_status.like("Validated%")),
        ).where(*filter_conds)
    )).one()

    tot_attempts, tot_unique, tot_conn, tot_unans, tot_val = summary_row
    tot_conn_pct = round((tot_conn / tot_attempts * 100), 1) if tot_attempts > 0 else 0.0
    tot_unans_pct = round((tot_unans / tot_attempts * 100), 1) if tot_attempts > 0 else 0.0
    tot_conv_pct = round((tot_val / tot_unique * 100), 1) if tot_unique > 0 else 0.0

    # Team TAT
    firsts = (
        select(CallAttempt.entry_id, func.min(CallAttempt.call_date).label("first"))
        .where(CallAttempt.company_id == user.company_id, *([CallAttempt.caller_id == caller_id] if caller_id else []))
        .group_by(CallAttempt.entry_id)
        .subquery()
    )
    tat = (await s.execute(
        select(
            func.count(),
            func.count().filter(firsts.c.first - SankalpEntry.entry_date <= cfg.first_attempt_target_days),
        )
        .select_from(firsts)
        .join(SankalpEntry, SankalpEntry.id == firsts.c.entry_id)
        .where(
            SankalpEntry.company_id == user.company_id,
            SankalpEntry.customer_validated,
            firsts.c.first >= first,
            firsts.c.first <= last,
        )
    )).one()

    # 3. Caller Comparative Matrix
    caller_rows = (await s.execute(
        select(
            CallAttempt.caller_id,
            func.count(CallAttempt.id),
            func.count(func.distinct(CallAttempt.entry_id)),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
            func.count().filter(CallAttempt.outcome.in_(R.UNANSWERED)),
            func.count().filter(CallAttempt.row_status.like("Validated%")),
        )
        .where(
            CallAttempt.company_id == user.company_id,
            CallAttempt.call_date >= first,
            CallAttempt.call_date <= last,
        )
        .group_by(CallAttempt.caller_id)
    )).all()
    caller_stats = {cid: (att, uniq, conn, unans, val) for cid, att, uniq, conn, unans, val in caller_rows}

    callers_list = []
    for u in callers_users:
        att, uniq, conn, unans, val = caller_stats.get(u.id, (0, 0, 0, 0, 0))
        c_pct = round((conn / att * 100), 1) if att > 0 else 0.0
        v_pct = round((val / uniq * 100), 1) if uniq > 0 else 0.0
        u_active = getattr(u, "status", "active") == "active" and (u.exit_date is None or u.exit_date >= today)

        callers_list.append({
            "caller_id": str(u.id),
            "name": u.full_name,
            "employee_code": u.employee_code,
            "languages": u.languages or [],
            "usual_branches": usual_branches_map.get(u.id, []),
            "is_absent_today": u.id in absent_ids,
            "active": u_active,
            "daily_limit": daily_limit,
            "today_load": loads_today.get(u.id, 0),
            "today_calls_made": made_today.get(u.id, 0),
            "attempts": att,
            "unique_entries": uniq,
            "connected": conn,
            "connect_pct": c_pct,
            "unanswered": unans,
            "validated": val,
            "conversion_pct": v_pct,
        })

    # Sort callers by attempts desc (ranking)
    callers_list.sort(key=lambda c: (c["attempts"], c["connected"]), reverse=True)

    # 4. Outcome breakdown
    outcome_counts = (await s.execute(
        select(CallAttempt.outcome, func.count(CallAttempt.id))
        .where(*filter_conds)
        .group_by(CallAttempt.outcome)
        .order_by(func.count(CallAttempt.id).desc())
    )).all()

    outcomes_list = []
    for outc, cnt in outcome_counts:
        pct = round((cnt / tot_attempts * 100), 1) if tot_attempts > 0 else 0.0
        grp = "positive" if outc == R.CONNECTED else ("unanswered" if outc in R.UNANSWERED else "discarded")
        outcomes_list.append({"outcome": outc, "count": cnt, "pct": pct, "group": grp})

    # 5. Slot distribution across 9 slots
    slot_counts = (await s.execute(
        select(
            CallAttempt.slot,
            func.count(CallAttempt.id),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
        )
        .where(*filter_conds)
        .group_by(CallAttempt.slot)
    )).all()
    slot_map = {s_name: (att, conn) for s_name, att, conn in slot_counts}
    slots_list = []
    for s_slot in R.SLOTS:
        s_att, s_conn = slot_map.get(s_slot, (0, 0))
        c_pct = round((s_conn / s_att * 100), 1) if s_att > 0 else 0.0
        slots_list.append({"slot": s_slot, "attempts": s_att, "connected": s_conn, "connect_pct": c_pct})

    # 6. Category Performance
    cat_counts = (await s.execute(
        select(
            SankalpEntry.category,
            func.count(func.distinct(CallAttempt.entry_id)),
            func.count(CallAttempt.id),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
            func.count().filter(CallAttempt.row_status.like("Validated%")),
        )
        .join(SankalpEntry, SankalpEntry.id == CallAttempt.entry_id)
        .where(*filter_conds)
        .group_by(SankalpEntry.category)
    )).all()

    category_list = []
    for cat_key, ent_cnt, att_cnt, conn_cnt, val_cnt in cat_counts:
        category_list.append({
            "category": cat_key,
            "label": R.CATEGORIES.get(cat_key, cat_key),
            "entries": ent_cnt,
            "attempts": att_cnt,
            "connected": conn_cnt,
            "validated": val_cnt,
            "connect_pct": round((conn_cnt / att_cnt * 100), 1) if att_cnt > 0 else 0.0,
        })

    # 7. Timeline Daily Trend
    trend_rows = (await s.execute(
        select(
            CallAttempt.call_date,
            func.count(CallAttempt.id),
            func.count().filter(CallAttempt.outcome == R.CONNECTED),
            func.count().filter(CallAttempt.row_status.like("Validated%")),
        )
        .where(*filter_conds)
        .group_by(CallAttempt.call_date)
        .order_by(CallAttempt.call_date.asc())
    )).all()
    trend_map = {cdate: (att, conn, val) for cdate, att, conn, val in trend_rows}

    trend_list = []
    days_span = (last - first).days + 1
    if days_span <= 62:
        curr_d = first
        while curr_d <= last:
            t_att, t_conn, t_val = trend_map.get(curr_d, (0, 0, 0))
            c_pct = round((t_conn / t_att * 100), 1) if t_att > 0 else 0.0
            trend_list.append({
                "date": str(curr_d),
                "day_label": curr_d.strftime("%d %b"),
                "attempts": t_att,
                "connected": t_conn,
                "validated": t_val,
                "connect_pct": c_pct,
            })
            curr_d += timedelta(days=1)
    else:
        for cdate in sorted(trend_map.keys()):
            t_att, t_conn, t_val = trend_map[cdate]
            c_pct = round((t_conn / t_att * 100), 1) if t_att > 0 else 0.0
            trend_list.append({
                "date": str(cdate),
                "day_label": cdate.strftime("%d %b"),
                "attempts": t_att,
                "connected": t_conn,
                "validated": t_val,
                "connect_pct": c_pct,
            })

    # 8. Recent 50 calls
    recent_query = (
        select(
            CallAttempt.id,
            CallAttempt.call_date,
            CallAttempt.slot,
            CallAttempt.created_at,
            CallAttempt.outcome,
            CallAttempt.row_status,
            CallAttempt.cycle,
            SankalpEntry.id,
            SankalpEntry.entry_code,
            SankalpEntry.person_name,
            SankalpEntry.phone,
            SankalpEntry.category,
            Branch.name,
            User.full_name,
        )
        .join(SankalpEntry, SankalpEntry.id == CallAttempt.entry_id)
        .join(Branch, Branch.id == SankalpEntry.branch_id)
        .join(User, User.id == CallAttempt.caller_id)
        .where(*filter_conds)
        .order_by(CallAttempt.created_at.desc())
        .limit(50)
    )
    recent_rows = (await s.execute(recent_query)).all()

    recent_calls = []
    for att_id, cdate, slot, cat_at, outc, rstat, cycle, eid, ecode, pname, phone, cat, bname, caller_name in recent_rows:
        recent_calls.append({
            "id": str(att_id),
            "call_date": str(cdate),
            "slot": slot,
            "created_at": cat_at.isoformat() if cat_at else None,
            "outcome": outc,
            "row_status": rstat,
            "cycle": cycle,
            "entry_id": str(eid),
            "entry_code": ecode,
            "person_name": pname,
            "phone": phone,
            "category": R.CATEGORIES.get(cat, cat),
            "branch_name": bname,
            "caller_name": caller_name,
        })

    num_callers = len(callers_users)
    avg_per_caller = round(tot_attempts / num_callers, 1) if num_callers > 0 else 0.0

    selected_caller_info = None
    if caller_id:
        c_user = next((u for u in callers_users if u.id == caller_id), None)
        if c_user:
            selected_caller_info = {
                "id": str(c_user.id),
                "name": c_user.full_name,
                "employee_code": c_user.employee_code,
            }

    return {
        "period": {
            "label": period,
            "from": str(first),
            "to": str(last),
        },
        "selected_caller": selected_caller_info,
        "summary": {
            "total_attempts": tot_attempts,
            "unique_entries": tot_unique,
            "connected_calls": tot_conn,
            "connected_pct": tot_conn_pct,
            "unanswered_calls": tot_unans,
            "unanswered_pct": tot_unans_pct,
            "validated_entries": tot_val,
            "conversion_pct": tot_conv_pct,
            "first_attempts_on_time": tat[1],
            "first_attempt_on_time_pct": round((tat[1] / tat[0] * 100), 1) if tat[0] > 0 else 0.0,
            "active_callers_count": num_callers,
            "avg_calls_per_caller": avg_per_caller,
            "total_capacity_today": num_callers * daily_limit,
            "today_calls_made": sum(made_today.values()),
        },
        "trend": trend_list,
        "callers": callers_list,
        "outcome_breakdown": outcomes_list,
        "slot_distribution": slots_list,
        "category_performance": category_list,
        "recent_calls": recent_calls,
    }


def _build_master_team_workbook(data: dict) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Executive Team Dashboard"
    ws.views.sheetView[0].showGridLines = True

    fill_navy = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    fill_subnavy = PatternFill(start_color="283079", end_color="283079", fill_type="solid")
    fill_card = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    font_banner = Font(name="Calibri", size=14, bold=True, color="1E1B4B")
    font_subbanner = Font(name="Calibri", size=11, color="64748B")
    font_section = Font(name="Calibri", size=12, bold=True, color="1E1B4B")
    font_white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_card_num = Font(name="Calibri", size=15, bold=True, color="1E1B4B")
    font_card_sub = Font(name="Calibri", size=10, bold=False, color="64748B")
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_data = Font(name="Calibri", size=11)

    thin = Side(border_style="thin", color="CBD5E1")
    box_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    summary = data["summary"]
    period = data["period"]

    # Sheet 1: Executive Team Dashboard
    ws.cell(row=1, column=1, value="AHAM HOUSING FINANCE · CALL CENTRE MASTER TEAM REPORT").font = font_banner
    ws.cell(
        row=2,
        column=1,
        value=f"Reporting Period: {period['from']} to {period['to']} ({period['label']}) · Total Callers: {summary['active_callers_count']}",
    ).font = font_subbanner

    cards = [
        ("TOTAL TEAM CALLS", f"{summary['total_attempts']:,}", f"{summary['unique_entries']:,} Unique Customers", 1, 2),
        ("TEAM CONNECT RATE", f"{summary['connected_pct']}%", f"{summary['connected_calls']:,} Connected Calls", 3, 4),
        ("VALIDATED CONVERSIONS", f"{summary['validated_entries']:,}", f"{summary['conversion_pct']}% Conversion Rate", 5, 6),
        ("AVG CALLS / CALLER", f"{summary['avg_calls_per_caller']}", f"{summary['first_attempt_on_time_pct']}% On-Time TAT", 7, 8),
    ]
    for title, val, sub, c1, c2 in cards:
        ws.merge_cells(start_row=4, start_column=c1, end_row=4, end_column=c2)
        ws.merge_cells(start_row=5, start_column=c1, end_row=5, end_column=c2)
        ws.merge_cells(start_row=6, start_column=c1, end_row=6, end_column=c2)

        ws.cell(row=4, column=c1, value=title).font = font_subbanner
        ws.cell(row=4, column=c1).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=5, column=c1, value=val).font = font_card_num
        ws.cell(row=5, column=c1).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=6, column=c1, value=sub).font = font_card_sub
        ws.cell(row=6, column=c1).alignment = Alignment(horizontal="center", vertical="center")

        for r in range(4, 7):
            for c in range(c1, c2 + 1):
                cell = ws.cell(row=r, column=c)
                cell.fill = fill_card
                cell.border = box_border

    # Outcome breakdown table
    ws.cell(row=8, column=1, value="Team Call Outcome Breakdown").font = font_section
    headers_outcome = ["Outcome", "Total Calls", "Share (%)", "Classification"]
    for c_idx, h in enumerate(headers_outcome, start=1):
        cell = ws.cell(row=9, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    cur_row = 10
    for ob in data.get("outcome_breakdown", []):
        ws.cell(row=cur_row, column=1, value=ob["outcome"]).font = font_bold
        ws.cell(row=cur_row, column=2, value=ob["count"]).font = font_data
        ws.cell(row=cur_row, column=3, value=f"{ob['pct']}%").font = font_data
        ws.cell(row=cur_row, column=4, value=ob["group"].title()).font = font_data
        for c in range(1, 5):
            ws.cell(row=cur_row, column=c).border = box_border
        cur_row += 1

    # Hourly Slots table
    ws.cell(row=8, column=6, value="Team Hourly Productivity Slots").font = font_section
    headers_slot = ["Slot", "Total Attempts", "Connected", "Connect (%)"]
    for c_idx, h in enumerate(headers_slot, start=6):
        cell = ws.cell(row=9, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_subnavy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    slot_row = 10
    for s_item in data.get("slot_distribution", []):
        ws.cell(row=slot_row, column=6, value=s_item["slot"]).font = font_bold
        ws.cell(row=slot_row, column=7, value=s_item["attempts"]).font = font_data
        ws.cell(row=slot_row, column=8, value=s_item["connected"]).font = font_data
        ws.cell(row=slot_row, column=9, value=f"{s_item['connect_pct']}%").font = font_data
        for c in range(6, 10):
            ws.cell(row=slot_row, column=c).border = box_border
        slot_row += 1

    # Product category table
    cat_start = max(cur_row, slot_row) + 2
    ws.cell(row=cat_start, column=1, value="Product Category Performance").font = font_section
    headers_cat = ["Category", "Entries Called", "Attempts", "Connected", "Validated", "Connect (%)"]
    for c_idx, h in enumerate(headers_cat, start=1):
        cell = ws.cell(row=cat_start + 1, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    c_row = cat_start + 2
    for cat_item in data.get("category_performance", []):
        ws.cell(row=c_row, column=1, value=cat_item["label"]).font = font_bold
        ws.cell(row=c_row, column=2, value=cat_item["entries"]).font = font_data
        ws.cell(row=c_row, column=3, value=cat_item["attempts"]).font = font_data
        ws.cell(row=c_row, column=4, value=cat_item["connected"]).font = font_data
        ws.cell(row=c_row, column=5, value=cat_item["validated"]).font = font_data
        ws.cell(row=c_row, column=6, value=f"{cat_item.get('connect_pct', 0)}%").font = font_data
        for c in range(1, 7):
            ws.cell(row=c_row, column=c).border = box_border
        c_row += 1

    # Sheet 2: Caller Performance Matrix (Comparative Table)
    ws2 = wb.create_sheet(title="Caller Performance Matrix")
    ws2.views.sheetView[0].showGridLines = True
    ws2.cell(row=1, column=1, value="CALLER PERFORMANCE MATRIX & LEADERBOARD").font = font_banner
    ws2.cell(row=2, column=1, value=f"Period: {period['from']} to {period['to']} · Ranked by Calls Made").font = font_subbanner

    headers_callers = [
        "Rank", "Caller Name", "Emp ID", "Languages", "Usual Branches",
        "Entries Called", "Calls Made", "Connected Calls", "Connect Rate (%)",
        "Unanswered Calls", "Entries Validated", "Conversion (%)", "Today's Load",
    ]
    for c_idx, h in enumerate(headers_callers, start=1):
        cell = ws2.cell(row=4, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    cp_row = 5
    for rank, clr in enumerate(data.get("callers", []), start=1):
        ws2.cell(row=cp_row, column=1, value=rank).font = font_bold
        ws2.cell(row=cp_row, column=2, value=clr["name"]).font = font_bold
        ws2.cell(row=cp_row, column=3, value=clr["employee_code"]).font = font_data
        ws2.cell(row=cp_row, column=4, value=", ".join(clr.get("languages", [])) or "—").font = font_data
        ws2.cell(row=cp_row, column=5, value=", ".join(clr.get("usual_branches", [])) or "None").font = font_data
        ws2.cell(row=cp_row, column=6, value=clr["unique_entries"]).font = font_data
        ws2.cell(row=cp_row, column=7, value=clr["attempts"]).font = font_bold
        ws2.cell(row=cp_row, column=8, value=clr["connected"]).font = font_data
        ws2.cell(row=cp_row, column=9, value=f"{clr['connect_pct']}%").font = font_bold
        ws2.cell(row=cp_row, column=10, value=clr["unanswered"]).font = font_data
        ws2.cell(row=cp_row, column=11, value=clr["validated"]).font = font_data
        ws2.cell(row=cp_row, column=12, value=f"{clr['conversion_pct']}%").font = font_data
        ws2.cell(row=cp_row, column=13, value=f"{clr['today_load']} / {clr['daily_limit']}").font = font_data

        for c in range(1, 14):
            ws2.cell(row=cp_row, column=c).border = box_border
        cp_row += 1

    # Sheet 3: Complete Call Attempts Log
    ws3 = wb.create_sheet(title="Call Attempts Log")
    ws3.views.sheetView[0].showGridLines = True
    ws3.cell(row=1, column=1, value="COMPLETE CALL ATTEMPTS AUDIT LOG").font = font_banner
    ws3.cell(row=2, column=1, value=f"Last {len(data.get('recent_calls', []))} Call Attempts Recorded Across All Callers").font = font_subbanner

    headers_team_log = ["Call Date", "Slot", "Caller", "Entry Code", "Customer Name", "Phone", "Category", "Branch", "Outcome", "Row Status"]
    for c_idx, h in enumerate(headers_team_log, start=1):
        cell = ws3.cell(row=4, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_subnavy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = box_border

    t_row = 5
    for rc in data.get("recent_calls", []):
        ws3.cell(row=t_row, column=1, value=rc["call_date"]).font = font_data
        ws3.cell(row=t_row, column=2, value=rc["slot"]).font = font_data
        ws3.cell(row=t_row, column=3, value=rc.get("caller_name", "—")).font = font_bold
        ws3.cell(row=t_row, column=4, value=rc["entry_code"]).font = font_bold
        ws3.cell(row=t_row, column=5, value=rc["person_name"]).font = font_data
        ws3.cell(row=t_row, column=6, value=rc["phone"]).font = font_data
        ws3.cell(row=t_row, column=7, value=rc["category"]).font = font_data
        ws3.cell(row=t_row, column=8, value=rc["branch_name"]).font = font_data
        ws3.cell(row=t_row, column=9, value=rc["outcome"]).font = font_bold
        ws3.cell(row=t_row, column=10, value=rc["row_status"] or "—").font = font_data
        for c in range(1, 11):
            ws3.cell(row=t_row, column=c).border = box_border
        t_row += 1

    for s_sheet in (ws, ws2, ws3):
        for col in s_sheet.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                val_str = str(cell.value or "")
                if "\n" in val_str:
                    val_str = max(val_str.split("\n"), key=len)
                if len(val_str) > max_len and cell.row > 2:
                    max_len = len(val_str)
            s_sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@router.get("/reports/callcentre/master-analytics/export.xlsx")
async def export_master_callcentre_analytics(
    period: str = "today",
    date_from: date | None = None,
    date_to: date | None = None,
    caller_id: uuid.UUID | None = None,
    user: User = Depends(require_perm("calls.manage")),
    s: AsyncSession = Depends(get_session),
):
    """Download comprehensive 3-sheet Master Call Centre Analytics Workbook in Excel format (.xlsx)."""
    data = await master_callcentre_analytics(period, date_from, date_to, caller_id, user, s)
    buf = _build_master_team_workbook(data)
    caller_suffix = f"_{data['selected_caller']['name'].replace(' ', '_')}" if data.get("selected_caller") else ""
    name = f"call_centre_analytics{caller_suffix}_{period}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )



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