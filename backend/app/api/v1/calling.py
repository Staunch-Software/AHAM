"""Call-centre portal (sections 5-8, 13.3): the daily run, callers' lists, recording calls, the lead card, the tracker."""
import re
import uuid
from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.deps import current_user, require_perm
from app.api.v1.entries import entry_row, get_scoped_entry
from app.core.db import get_session
from app.models import (
    Branch,
    BranchAnswer,
    CallAllocation,
    CallAttempt,
    CallerAbsence,
    CallerDay,
    Company,
    FollowupTracker,
    LeadCard,
    Region,
    SankalpEntry,
    SelectionRun,
    User,
)
from app.services.periods import tz_of
from app.services.phone import clean_phone
from app.services.reference import audit
from app.services.sankalp import call_sheet as CS
from app.services.sankalp import callers as CL
from app.services.sankalp import rules as R
from app.services.sankalp.handoff import review_green_channel, save_tracker
from app.services.sankalp.ops import absent_callers, company_today, record_attempt, run_selection, save_lead_card
from app.services.sankalp.schemas import AttemptIn, LeadCardIn, TrackerIn
from app.services.sankalp.views import calling_detail, current_status
from app.services.settings import load_settings
from app.services.tabular import parse_date

router = APIRouter(tags=["call centre"])
require_work = require_perm("calls.work")
require_manage = require_perm("calls.manage")
KIND_ORDER = {"priority": 0, "retry": 1, "followup": 2, "fresh": 3}


@router.get("/sankalp/meta")
async def meta(user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    """The fixed lists of the business logic, so every screen uses the same words, and the current windows and
    limits (section 14), so screen texts follow the settings."""
    cfg = await load_settings(s, user.company_id)
    return {
        "limits": {k: getattr(cfg, k) for k in (
            "repeat_window_days", "max_unanswered_lead", "tries_per_day_lead", "tries_per_day_dsa", "max_slots_per_day",
            "first_attempt_target_days", "action_window_days", "correct_number_window_days",
            "amber_correction_window_days", "branch_date_threshold_days", "daily_entry_target", "daily_lead_target",
            "green_channel_construction_limit", "green_channel_purchase_limit")},
        "categories": [{"key": k, "label": v, "call_group": R.CALL_GROUP[k]} for k, v in R.CATEGORIES.items()],
        "slots": R.SLOTS, "outcomes": R.OUTCOMES, "unanswered": sorted(R.UNANSWERED),
        "questions": {"name_check": R.NAME_CHECK, "visit": R.VISIT, "relationship": R.RELATIONSHIP,
                      "loan_need": R.LOAN_NEED, "timeline": R.TIMELINE, "income": R.INCOME, "documents": R.DOCUMENTS,
                      "next_step": R.NEXT_STEP, "purpose": R.PURPOSE, "own_contribution": R.OWN_CONTRIBUTION,
                      "dsa_rag": R.DSA_RAG},
        "branch_codes": [{"code": k, "meaning": m, "date_label": d} for k, (m, d) in R.BRANCH_CODES.items()],
        "statuses": R.ALL_STATUSES, "lead_outcomes": R.LEAD_OUTCOMES, "rags": R.RAGS,
        "tracker": {"owners": R.TRACKER_OWNERS, "outcomes": R.TRACKER_OUTCOMES, "action_types": R.TRACKER_ACTION_TYPES,
                    "reject_reasons": R.TRACKER_REJECT_REASONS},
    }


async def _rows_for(s: AsyncSession, allocs: list[CallAllocation], today: date) -> list[dict]:
    if not allocs:
        return []
    target = (await load_settings(s, allocs[0].company_id)).first_attempt_target_days
    ids = [a.entry_id for a in allocs]
    rows = {r[0].id: r for r in (await s.execute(
        select(SankalpEntry, User, Branch, Region).join(User, User.id == SankalpEntry.so_user_id)
        .join(Branch, Branch.id == SankalpEntry.branch_id).outerjoin(Region, Region.id == Branch.region_id)
        .where(SankalpEntry.id.in_(ids)))).all()}
    tries = dict((await s.execute(select(CallAttempt.entry_id, func.count()).where(
        CallAttempt.entry_id.in_(ids), CallAttempt.call_date == today).group_by(CallAttempt.entry_id))).all())
    callers = dict((await s.execute(select(User.id, User.full_name).where(
        User.id.in_({a.caller_id for a in allocs if a.caller_id} or {uuid.uuid4()})))).all())
    out = []
    for a in sorted(allocs, key=lambda a: (KIND_ORDER.get(a.kind, 9), rows[a.entry_id][0].submitted_at_device,
                                           rows[a.entry_id][0].entry_code)):
        out.append({**entry_row(*rows[a.entry_id]), "allocation_id": str(a.id), "kind": a.kind, "run_date": a.run_date,
                    "caller_id": str(a.caller_id) if a.caller_id else None, "caller": callers.get(a.caller_id),
                    "tries_today": tries.get(a.entry_id, 0), "unanswered_count": rows[a.entry_id][0].unanswered_count,
                    # 6: first attempt within the target (setting, days after the entry date)
                    "first_try_overdue": _overdue(rows[a.entry_id][0], today, target)})
    return out


def _overdue(e: SankalpEntry, today: date, target_days: int) -> bool:
    return e.last_called_on is None and (today - e.entry_date).days > target_days


@router.get("/calls/my-list")
async def my_list(caller_id: uuid.UUID | None = None, user: User = Depends(require_work),
                  s: AsyncSession = Depends(get_session)):
    """Today's work: PRIORITY first, then retries due, follow-ups, and new entries. The master owner may look at
    any caller's list."""
    who = caller_id if caller_id and user.role == "master_owner" else user.id
    allocs = (await s.execute(select(CallAllocation).where(CallAllocation.company_id == user.company_id,
                                                           CallAllocation.caller_id == who,
                                                           CallAllocation.status == "open"))).scalars().all()
    today = await company_today(s, user.company_id)
    # 7.1: a lead gets two planned tries a day and leaves the list after them, but up to three may be recorded;
    # those still in retry stay reachable today for that third try
    done = (await s.execute(select(CallAllocation).where(CallAllocation.company_id == user.company_id,
                                                         CallAllocation.caller_id == who, CallAllocation.run_date == today,
                                                         CallAllocation.status == "done"))).scalars().all()
    slots = (await load_settings(s, user.company_id)).max_slots_per_day
    called_today = [r for r in await _rows_for(s, list(done), today)
                    if r["status"] == R.IN_RETRY and r["call_group"] == "lead" and r["tries_today"] < slots
                    and not (r["callback_date"] and r["callback_date"] > today)]
    return {"today": today, "items": await _rows_for(s, list(allocs), today), "called_today": called_today}


@router.get("/calls/history")
async def call_history(
    caller_id: uuid.UUID | None = None,
    q: str | None = None,
    outcome: str | None = None,
    branch_id: uuid.UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    user: User = Depends(require_work),
    s: AsyncSession = Depends(get_session),
):
    """The history of calls made by the caller (or all callers if master owner)."""
    who = caller_id if (caller_id and user.role == "master_owner") else (user.id if user.role != "master_owner" else None)

    SoUser = aliased(User, name="so_user")
    CallerUser = aliased(User, name="caller_user")

    stmt = (
        select(CallAttempt, SankalpEntry, Branch, SoUser, CallerUser, LeadCard.lead_id)
        .join(SankalpEntry, SankalpEntry.id == CallAttempt.entry_id)
        .join(Branch, Branch.id == SankalpEntry.branch_id)
        .join(CallerUser, CallerUser.id == CallAttempt.caller_id)
        .outerjoin(SoUser, SoUser.id == SankalpEntry.so_user_id)
        .outerjoin(LeadCard, LeadCard.entry_id == SankalpEntry.id)
        .where(CallAttempt.company_id == user.company_id)
    )

    if who:
        stmt = stmt.where(CallAttempt.caller_id == who)

    if q:
        like = f"%{q.strip()}%"
        phone_match = f"%{clean_phone(q) or q.strip()}%"
        stmt = stmt.where(
            or_(
                SankalpEntry.entry_code.ilike(like),
                SankalpEntry.person_name.ilike(like),
                SankalpEntry.phone.like(phone_match),
                SoUser.full_name.ilike(like),
            )
        )

    if outcome:
        stmt = stmt.where(CallAttempt.outcome == outcome)

    if branch_id:
        stmt = stmt.where(SankalpEntry.branch_id == branch_id)

    try:
        df, dt = parse_date(date_from), parse_date(date_to)
    except ValueError as e:
        raise HTTPException(422, str(e))

    if df:
        stmt = stmt.where(CallAttempt.call_date >= df)
    if dt:
        stmt = stmt.where(CallAttempt.call_date <= dt)

    total = (await s.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()

    rows = (
        await s.execute(
            stmt.order_by(CallAttempt.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = []
    for attempt, e, branch, so, caller_u, lead_id in rows:
        items.append({
            "id": str(attempt.id),
            "entry_id": str(e.id),
            "entry_code": e.entry_code,
            "person_name": e.person_name,
            "phone": e.phone,
            "category": e.category,
            "category_label": R.CATEGORIES.get(e.category, e.category),
            "call_group": e.call_group,
            "branch_id": str(branch.id),
            "branch_name": branch.name,
            "so_name": so.full_name if so else None,
            "caller_id": str(caller_u.id),
            "caller_name": caller_u.full_name if caller_u else None,
            "call_date": attempt.call_date,
            "slot": attempt.slot,
            "outcome": attempt.outcome,
            "cycle": attempt.cycle,
            "next_date": attempt.next_date,
            "row_status": attempt.row_status,
            "answers": attempt.answers,
            "created_at": attempt.created_at,
            "current_status": current_status(e),
            "rag": e.rag_override or e.rag,
            "lead_id": lead_id,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/calls/entries/{entry_id}/attempts", status_code=201)
async def add_attempt(entry_id: uuid.UUID, body: AttemptIn, user: User = Depends(require_work),
                      s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    await s.execute(select(SankalpEntry.id).where(SankalpEntry.id == e.id).with_for_update())
    a = await record_attempt(s, e, user, body)
    await s.commit()
    return {"attempt_id": str(a.id), "row_status": a.row_status, "status": e.status, "rag": e.rag_override or e.rag,
            "unanswered_count": e.unanswered_count, "so_action": e.so_action, "cc_action": e.cc_action,
            **(await calling_detail(s, user, e))}


@router.put("/calls/entries/{entry_id}/lead-card")
async def put_lead_card(entry_id: uuid.UUID, body: LeadCardIn, user: User = Depends(require_work),
                        s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    await save_lead_card(s, e, user, body)
    await s.commit()
    return (await calling_detail(s, user, e))["lead_card"]


# ---------------------------------------------------------------- master owner: daily run and allocation
class RunIn(BaseModel):
    run_date: date | None = None


@router.post("/calls/runs")
async def start_run(body: RunIn, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    today = await company_today(s, user.company_id)
    run_date = body.run_date or today
    if run_date > today:
        raise HTTPException(422, "The run date cannot be in the future")
    result = await run_selection(s, user.company_id, run_date, user)
    audit(s, user, "selection.run", "company", user.company_id)
    await s.commit()
    return result


@router.get("/calls/runs")
async def list_runs(user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(SelectionRun, User.full_name).outerjoin(User, User.id == SelectionRun.started_by)
                            .where(SelectionRun.company_id == user.company_id)
                            .order_by(SelectionRun.started_at.desc()).limit(60))).all()
    return [{"id": str(r.id), "run_date": r.run_date, "started_at": r.started_at, "started_by": n or "Automatic",
             "counts": r.counts} for r, n in rows]


CALL_TYPE = {"retry": "Retry", "followup": "Follow-up"}
YES_NO = {True: "Yes", False: "No"}
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def _call_type(a: CallAllocation, e: SankalpEntry) -> str:
    if a.kind == "fresh":
        return "New lead" if e.call_group == "lead" else "New DSA/CP"
    if a.kind == "priority":
        return f"PRIORITY ({e.priority_reason})" if e.priority_reason else "PRIORITY"
    return CALL_TYPE.get(a.kind, a.kind)


def _history(before: list[CallAttempt], names: dict) -> str:
    """The calls before the sheet's day, in one cell: how many, and the last one."""
    if not before:
        return ""
    t = before[-1]
    return (f"{len(before)} earlier {'try' if len(before) == 1 else 'tries'} · last {t.call_date:%d-%b} {t.slot}: "
            f"{t.outcome} ({names.get(t.caller_id, '')}){f' → {t.row_status}' if t.row_status else ''}")


@router.get("/calls/call-sheet.xlsx")
async def call_sheet(day: date | None = None, caller_id: uuid.UUID | None = None, user: User = Depends(require_work),
                     s: AsyncSession = Depends(get_session)):
    """The callers' lists for a day as one Excel file, one sheet per caller, in the layout of the call sheets the
    Master owner hands out today: lead details, the tries and answers recorded in the app, and the lead card. The
    Master owner gets every caller (or the one asked for, plus the work with no caller when none is asked for);
    a caller gets their own."""
    today = await company_today(s, user.company_id)
    day = day or today
    if user.role != "master_owner":
        caller_id = user.id
    q = select(CallAllocation).where(CallAllocation.company_id == user.company_id, CallAllocation.run_date == day)
    if caller_id:
        q = q.where(CallAllocation.caller_id == caller_id)
    allocs: dict = {}
    for a in (await s.execute(q.order_by(CallAllocation.created_at))).scalars().all():
        allocs[(a.caller_id, a.entry_id)] = a  # one row per entry on a list, the latest allocation of the day
    ids = list({e for _, e in allocs} or {uuid.uuid4()})
    rows = {r[0].id: r for r in (await s.execute(
        select(SankalpEntry, User.full_name, Branch.name).join(User, User.id == SankalpEntry.so_user_id)
        .join(Branch, Branch.id == SankalpEntry.branch_id).where(SankalpEntry.id.in_(ids)))).all()}
    attempts: dict = {}
    for t in (await s.execute(select(CallAttempt).where(CallAttempt.entry_id.in_(ids))
                              .order_by(CallAttempt.created_at))).scalars().all():
        attempts.setdefault(t.entry_id, []).append(t)
    cards = {c.entry_id: c for c in (await s.execute(select(LeadCard).where(LeadCard.entry_id.in_(ids)))).scalars().all()}
    people = {caller_id} | {c for c, _ in allocs} | {t.caller_id for ts in attempts.values() for t in ts}
    names = dict((await s.execute(select(User.id, User.full_name).where(
        User.id.in_({p for p in people if p} or {uuid.uuid4()})))).all())
    branch_names = dict((await s.execute(select(Branch.id, Branch.name).where(
        Branch.id.in_({c.handling_branch_id for c in cards.values() if c.handling_branch_id} or {uuid.uuid4()})))).all())
    cfg = await load_settings(s, user.company_id)

    def row(a: CallAllocation) -> CS.SheetRow:
        e, so_name, branch = rows[a.entry_id]
        mine = attempts.get(e.id, [])
        on_day = [t for t in mine if t.call_date == day][:3]
        talked = [t for t in on_day if t.outcome == R.CONNECTED and t.answers]
        ans = talked[-1].answers if talked else {}
        callback = next((t.next_date for t in reversed(on_day) if t.next_date), None)
        card = cards.get(e.id)
        d = card.data if card else {}
        tries = [x for t in on_day for x in (t.slot, t.outcome)] + [None] * (6 - 2 * len(on_day))
        vehicle = d.get("vehicle")
        cells = [
            names.get(a.caller_id, "No caller"), day, e.entry_code, _call_type(a, e), R.CATEGORIES.get(e.category),
            "Lead" if e.call_group == "lead" else "DSA/CP", e.entry_date, so_name, branch, e.person_name, e.phone,
            e.description, cfg.max_unanswered_lead - e.unanswered_count if e.call_group == "lead" else None,
            e.callback_date, _history([t for t in mine if t.call_date < day], names),
            *tries, ans.get("dsa_rag"), ans.get("needs_home_loan"), ans.get("name_check"), ans.get("name_given"),
            ans.get("visit"), ans.get("relationship"), ans.get("loan_need"), ans.get("timeline"), ans.get("income"),
            ans.get("documents"), ans.get("next_step"), ans.get("next_date") or callback, ans.get("purpose"),
            ans.get("own_contribution"), ans.get("remarks"), card.lead_id if card else None,
            branch_names.get(card.handling_branch_id) if card else None, d.get("age"), d.get("date_of_birth"),
            d.get("address"), d.get("property_pincode"), d.get("business_pincode"), d.get("city"),
            YES_NO.get(d.get("payslip_or_itr")), d.get("job_profile"), d.get("individual_monthly_income"),
            d.get("family_monthly_income"),
            None if vehicle is None else (f"Yes – {d['vehicle_type']}" if vehicle and d.get("vehicle_type") else YES_NO[vehicle]),
            d.get("cibil_score"), YES_NO.get(d.get("bounce_last_6_months")), d.get("property_owner"),
            d.get("property_area"), d.get("approved_property"), d.get("loan_purpose"),
            card.loan_requirement if card else None, d.get("property_type"),
        ]
        # dates kept as text in the answers and the card ("2026-10-24") become real dates in Excel
        cells = [date.fromisoformat(v) if isinstance(v, str) and ISO_DAY.fullmatch(v) else v for v in cells]
        return CS.SheetRow(cells, e.call_group, ans.get("needs_home_loan") == "Yes")

    by_caller: dict = {}
    for (c, _), a in allocs.items():
        by_caller.setdefault(c, []).append(a)
    if caller_id and caller_id not in by_caller:
        by_caller[caller_id] = []
    order = sorted(by_caller, key=lambda c: (c is None, names.get(c, "")))
    sheets = [(names.get(c, "No caller"), [row(a) for a in sorted(
        by_caller[c], key=lambda a: (KIND_ORDER.get(a.kind, 9), rows[a.entry_id][0].submitted_at_device,
                                     rows[a.entry_id][0].entry_code))]) for c in order]
    tz = tz_of((await s.get(Company, user.company_id)).timezone)
    data = CS.build(day, sheets, cfg.max_unanswered_lead, datetime.now(tz))
    who = re.sub(r"[^A-Za-z0-9]+", "_", names.get(caller_id, "")).strip("_") if caller_id else "all_callers"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="call_sheet_{who}_{day}.xlsx"'})


class CallerDayItem(BaseModel):
    branch_id: uuid.UUID
    caller_id: uuid.UUID | None


class CallerDaysIn(BaseModel):
    day: date
    assignments: list[CallerDayItem]


@router.get("/calls/caller-days")
async def get_caller_days(day: date | None = None, user: User = Depends(require_manage),
                          s: AsyncSession = Depends(get_session)):
    day = day or await company_today(s, user.company_id)
    rows = dict((await s.execute(select(CallerDay.branch_id, CallerDay.caller_id).where(
        CallerDay.company_id == user.company_id, CallerDay.day == day))).all())
    branches = (await s.execute(select(Branch, Region.name).outerjoin(Region, Region.id == Branch.region_id).where(
        Branch.company_id == user.company_id, Branch.status == "active").order_by(Region.name, Branch.name))).all()
    uncalled_counts = dict((await s.execute(
        select(SankalpEntry.branch_id, func.count(SankalpEntry.id)).where(
            SankalpEntry.company_id == user.company_id,
            SankalpEntry.status.is_(None),
            SankalpEntry.call_group.in_(["lead", "dsa_cp"]),
        ).group_by(SankalpEntry.branch_id)
    )).all())
    return {"day": day, "items": [{"branch_id": str(b.id), "branch": b.name, "region": rn,
                                   "caller_id": str(rows[b.id]) if b.id in rows else None,
                                   "uncalled_count": uncalled_counts.get(b.id, 0)} for b, rn in branches]}


@router.put("/calls/caller-days")
async def put_caller_days(body: CallerDaysIn, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    """Each morning: one caller per branch. New entries of that branch go to this caller."""
    callers = set((await s.execute(select(User.id).where(User.company_id == user.company_id, User.role == "caller",
                                                         User.status == "active"))).scalars().all())
    branches = set((await s.execute(select(Branch.id).where(Branch.company_id == user.company_id))).scalars().all())
    before = dict((await s.execute(select(CallerDay.branch_id, CallerDay.caller_id).where(
        CallerDay.company_id == user.company_id, CallerDay.day == body.day))).all())
    for it in body.assignments:
        if it.branch_id not in branches or (it.caller_id and it.caller_id not in callers):
            raise HTTPException(422, "Unknown branch or caller")
        if it.caller_id is None:
            await s.execute(CallerDay.__table__.delete().where(and_(CallerDay.branch_id == it.branch_id, CallerDay.day == body.day)))
            continue
        stmt = pg_insert(CallerDay).values(branch_id=it.branch_id, day=body.day, company_id=user.company_id,
                                           caller_id=it.caller_id, set_by=user.id)
        await s.execute(stmt.on_conflict_do_update(index_elements=["branch_id", "day"],
                                                   set_={"caller_id": stmt.excluded.caller_id, "set_by": user.id}))
    # The branch's work for that day follows the newly set caller: entries waiting without a caller, and, when the
    # branch's caller changed, its new entries still waiting for their first call on the old caller's list. Retries
    # stay with their first caller, and a branch whose caller did not change is left alone (a list moved for an absent
    # caller stays moved).
    moved = 0
    for it in body.assignments:
        if not it.caller_id:
            continue
        branch_entries = select(SankalpEntry.id).where(SankalpEntry.branch_id == it.branch_id)
        waiting = [and_(CallAllocation.caller_id.is_(None), CallAllocation.entry_id.in_(branch_entries))]
        old = before.get(it.branch_id)
        if old and old != it.caller_id:
            waiting.append(and_(CallAllocation.caller_id == old, CallAllocation.kind == "fresh",
                                CallAllocation.entry_id.in_(branch_entries.where(SankalpEntry.last_called_on.is_(None)))))
        res = await s.execute(CallAllocation.__table__.update().where(and_(
            CallAllocation.company_id == user.company_id, CallAllocation.status == "open",
            CallAllocation.run_date == body.day, or_(*waiting))).values(caller_id=it.caller_id))
        moved += res.rowcount
    audit(s, user, "caller_days.set", "company", user.company_id, details={"moved": moved} if moved else None)
    await s.commit()
    return {**await get_caller_days(body.day, user, s), "moved": moved}


class CopyIn(BaseModel):
    from_day: date
    to_day: date


@router.post("/calls/caller-days/copy")
async def copy_caller_days(body: CopyIn, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    # "Copy yesterday" on a Monday (or after a holiday) copies the last day that had callers set, not the empty Sunday.
    last = (await s.execute(select(func.max(CallerDay.day)).where(
        CallerDay.company_id == user.company_id, CallerDay.day <= body.from_day))).scalar()
    rows = (await s.execute(select(CallerDay.branch_id, CallerDay.caller_id).where(
        CallerDay.company_id == user.company_id, CallerDay.day == last))).all() if last else []
    items = [CallerDayItem(branch_id=b, caller_id=c) for b, c in rows]
    return await put_caller_days(CallerDaysIn(day=body.to_day, assignments=items), user, s)


# ---------------------------------------------------------------- callers: languages, absence, the daily limit
def _languages(values: list[str], allowed: list[str]) -> list[str]:
    canon = {a.strip().lower(): a for a in allowed}
    out: list[str] = []
    for v in values:
        k = v.strip().lower()
        if k not in canon:
            raise HTTPException(422, f"'{v}' is not one of the languages in Settings ({', '.join(allowed)})")
        if canon[k] not in out:
            out.append(canon[k])
    return out


async def _day_state(s: AsyncSession, company_id: uuid.UUID, day: date):
    """Branches and callers as the allocation rules see them on a day (app/services/sankalp/callers.py). A caller's
    list counts the day's allocations, and, before the run, the retries due to them; a branch carries the new entries
    still waiting for the selection, counted on the caller who takes it."""
    cfg = await load_settings(s, company_id)
    today_caller = dict((await s.execute(select(CallerDay.branch_id, CallerDay.caller_id).where(
        CallerDay.company_id == company_id, CallerDay.day == day))).all())
    absent = await absent_callers(s, company_id, day)
    users = (await s.execute(select(User).where(User.company_id == company_id, User.role == "caller")
                             .order_by(User.full_name))).scalars().all()
    listed = dict((await s.execute(select(CallAllocation.caller_id, func.count()).where(
        CallAllocation.company_id == company_id, CallAllocation.run_date == day, CallAllocation.status.in_(["open", "done"]),
        CallAllocation.caller_id.is_not(None)).group_by(CallAllocation.caller_id))).all())
    on_a_list = select(CallAllocation.entry_id).where(CallAllocation.company_id == company_id, CallAllocation.run_date == day)
    not_closed = or_(SankalpEntry.lead_outcome.is_(None), SankalpEntry.lead_outcome.notin_(R.CLOSED_OUTCOMES))
    retries = dict((await s.execute(select(SankalpEntry.first_caller_id, func.count()).where(
        SankalpEntry.company_id == company_id, SankalpEntry.status == R.IN_RETRY, not_closed,
        or_(SankalpEntry.callback_date.is_(None), SankalpEntry.callback_date <= day),
        or_(SankalpEntry.last_called_on.is_(None), SankalpEntry.last_called_on < day),
        SankalpEntry.id.notin_(on_a_list)).group_by(SankalpEntry.first_caller_id))).all())
    before = SankalpEntry.entry_date <= day if cfg.same_day_calling else SankalpEntry.entry_date < day
    waiting = dict((await s.execute(select(SankalpEntry.branch_id, func.count()).where(
        SankalpEntry.company_id == company_id, SankalpEntry.selection_status.is_(None),
        SankalpEntry.call_group.in_(["lead", "dsa_cp"]), SankalpEntry.entry_date >= cfg.first_call_date, before)
        .group_by(SankalpEntry.branch_id))).all())
    fresh: dict = defaultdict(dict)
    for b, c, n in (await s.execute(
            select(SankalpEntry.branch_id, CallAllocation.caller_id, func.count())
            .join(SankalpEntry, SankalpEntry.id == CallAllocation.entry_id)
            .where(CallAllocation.company_id == company_id, CallAllocation.status == "open", CallAllocation.run_date == day,
                   CallAllocation.kind == "fresh", SankalpEntry.last_called_on.is_(None))
            .group_by(SankalpEntry.branch_id, CallAllocation.caller_id))).all():
        fresh[b][c] = n
    callers = [CL.CallerToday(u.id, u.full_name, list(u.languages or []), u.status == "active", u.id in absent,
                              listed.get(u.id, 0) + retries.get(u.id, 0)) for u in users]
    rows = (await s.execute(select(Branch, Region.name).outerjoin(Region, Region.id == Branch.region_id).where(
        Branch.company_id == company_id, Branch.status == "active").order_by(Region.name, Branch.name))).all()
    branches = [CL.BranchToday(b.id, b.name, rn, list(b.languages or []), b.usual_caller_id, today_caller.get(b.id),
                               waiting.get(b.id, 0), fresh.get(b.id, {})) for b, rn in rows]
    return branches, callers, users, cfg


def _who(c: CL.CallerToday | None) -> dict | None:
    return {"caller_id": str(c.id), "caller": c.name} if c else None


@router.get("/calls/callers")
async def list_callers(day: date | None = None, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    """The Callers page: every caller with their languages, usual branches, absence and today's list against the
    limit; and every branch with its languages and usual caller."""
    day = day or await company_today(s, user.company_id)
    branches, callers, users, cfg = await _day_state(s, user.company_id, day)
    load = CL.loads(branches, callers)
    made = dict((await s.execute(select(CallAttempt.caller_id, func.count()).where(
        CallAttempt.company_id == user.company_id, CallAttempt.call_date == day).group_by(CallAttempt.caller_id))).all())
    code = {u.id: u.employee_code for u in users}
    names = {c.id: c.name for c in callers}
    return {
        "day": day, "limit": cfg.caller_daily_limit, "languages": cfg.call_languages,
        "callers": [{"id": str(c.id), "name": c.name, "employee_code": code[c.id], "active": c.active, "absent": c.absent,
                     "languages": c.languages, "usual_branches": [b.name for b in branches if b.usual == c.id],
                     "today_branches": [b.name for b in branches if CL.holder(b) == c.id],
                     "load": load[c.id], "room": cfg.caller_daily_limit - load[c.id], "calls_made": made.get(c.id, 0)}
                    for c in callers],
        "branches": [{"branch_id": str(b.id), "branch": b.name, "region": b.region, "languages": b.languages,
                      "usual_caller_id": str(b.usual) if b.usual else None, "usual_caller": names.get(b.usual)}
                     for b in branches],
    }


@router.get("/calls/day-plan")
async def day_plan(day: date | None = None, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    """The Daily run page's flags and suggestions: per branch who takes it and what is wrong (no caller, absent, does
    not speak the language, over the limit) with a suggested caller; per caller the list against the limit; and the
    moves that bring a caller over the limit back under it. Nothing changes until the Master owner applies one."""
    day = day or await company_today(s, user.company_id)
    branches, callers, _, cfg = await _day_state(s, user.company_id, day)
    limit = cfg.caller_daily_limit
    plan = CL.day_plan(branches, callers, limit)
    load = plan["load"]
    return {
        "day": day, "limit": limit,
        "branches": [{"branch_id": str(r["branch"].id), "branch": r["branch"].name, "region": r["branch"].region,
                      "languages": r["branch"].languages, "waiting": r["branch"].waiting,
                      "new_on_lists": sum(r["branch"].fresh_open.values()), **(_who(r["caller"]) or {"caller_id": None, "caller": None}),
                      "flags": r["flags"],
                      "suggestion": {**_who(r["suggestion"]), "room": limit - load.get(r["suggestion"].id, 0)} if r["suggestion"] else None}
                     for r in plan["branches"]],
        "callers": [{"id": str(c.id), "name": c.name, "active": c.active, "absent": c.absent, "languages": c.languages,
                     "load": load[c.id], "room": limit - load[c.id], "over": max(0, load[c.id] - limit)} for c in callers],
        "moves": [{"kind": m["kind"], "from_id": str(m["from"].id), "from": m["from"].name, "to_id": str(m["to"].id),
                   "to": m["to"].name, "branch_id": str(m["branch"].id), "branch": m["branch"].name, "count": m["count"],
                   "languages": m["branch"].languages} for m in plan["moves"]],
    }


class CallerIn(BaseModel):
    languages: list[str] = Field(max_length=20)


@router.patch("/calls/callers/{caller_id}")
async def set_caller(caller_id: uuid.UUID, body: CallerIn, user: User = Depends(require_manage),
                     s: AsyncSession = Depends(get_session)):
    c = await s.get(User, caller_id)
    if not c or c.company_id != user.company_id or c.role != "caller":
        raise HTTPException(404, "Caller not found")
    before = list(c.languages or [])
    c.languages = _languages(body.languages, (await load_settings(s, user.company_id)).call_languages)
    audit(s, user, "caller.languages", "user", c.id, details={"languages": [before, c.languages]})
    await s.commit()
    return {"id": str(c.id), "languages": c.languages}


class AbsenceIn(BaseModel):
    day: date
    absent: bool


@router.put("/calls/callers/{caller_id}/absence")
async def set_absence(caller_id: uuid.UUID, body: AbsenceIn, user: User = Depends(require_manage),
                      s: AsyncSession = Depends(get_session)):
    """The Master owner marks a caller absent (or present again) for a day. An absent caller gets no work from the run
    that day, and their branches are flagged with a suggested caller."""
    c = await s.get(User, caller_id)
    if not c or c.company_id != user.company_id or c.role != "caller":
        raise HTTPException(404, "Caller not found")
    if body.absent:
        await s.execute(pg_insert(CallerAbsence).values(id=uuid.uuid4(), company_id=user.company_id, caller_id=c.id,
                                                        day=body.day, marked_by=user.id).on_conflict_do_nothing(
            index_elements=["caller_id", "day"]))
    else:
        await s.execute(CallerAbsence.__table__.delete().where(and_(CallerAbsence.caller_id == c.id,
                                                                    CallerAbsence.day == body.day)))
    audit(s, user, "caller.absent" if body.absent else "caller.present", "user", c.id, details={"day": body.day.isoformat()})
    await s.commit()
    return {"id": str(c.id), "day": body.day, "absent": body.absent}


class BranchCallingIn(BaseModel):
    languages: list[str] | None = Field(None, max_length=20)
    usual_caller_id: uuid.UUID | None = None


@router.put("/calls/branches/{branch_id}")
async def set_branch_calling(branch_id: uuid.UUID, body: BranchCallingIn, user: User = Depends(require_manage),
                             s: AsyncSession = Depends(get_session)):
    """A branch's languages and its usual caller (only the fields sent change; usual_caller_id null clears it)."""
    b = await s.get(Branch, branch_id)
    if not b or b.company_id != user.company_id:
        raise HTTPException(404, "Branch not found")
    changes: dict = {}
    if "languages" in body.model_fields_set and body.languages is not None:
        langs = _languages(body.languages, (await load_settings(s, user.company_id)).call_languages)
        changes["languages"] = [list(b.languages or []), langs]
        b.languages = langs
    if "usual_caller_id" in body.model_fields_set:
        if body.usual_caller_id:
            c = await s.get(User, body.usual_caller_id)
            if not c or c.company_id != user.company_id or c.role != "caller":
                raise HTTPException(422, "Pick a caller")
        changes["usual_caller_id"] = [str(b.usual_caller_id) if b.usual_caller_id else None,
                                      str(body.usual_caller_id) if body.usual_caller_id else None]
        b.usual_caller_id = body.usual_caller_id
    audit(s, user, "branch.calling", "branch", b.id, details=changes or None)
    await s.commit()
    return {"branch_id": str(b.id), "languages": b.languages, "usual_caller_id": str(b.usual_caller_id) if b.usual_caller_id else None}


class DayIn(BaseModel):
    day: date


@router.post("/calls/caller-days/auto")
async def auto_caller_days(body: DayIn, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    """Today's caller for every branch by the rules: its usual caller when present and speaking the language,
    otherwise the present caller who speaks it with the most room. A branch nobody can take keeps what it had."""
    branches, callers, _, cfg = await _day_state(s, user.company_id, body.day)
    pick = CL.auto_assign(branches, callers, cfg.caller_daily_limit)
    items = [CallerDayItem(branch_id=b, caller_id=c) for b, c in pick.items() if c]
    res = await put_caller_days(CallerDaysIn(day=body.day, assignments=items), user, s)
    names = {b.id: b.name for b in branches}
    return {**res, "auto": {"assigned": len(items), "no_caller": sorted(names[b] for b, c in pick.items() if not c)}}


@router.get("/calls/allocations")
async def allocations(day: date | None = None, unassigned: bool = False, user: User = Depends(require_manage),
                      s: AsyncSession = Depends(get_session)):
    """The master owner's overview: open work per caller, and work with no caller yet. The per-caller counts always
    cover all open work; `items` is only the work with no caller (`unassigned` is kept for older clients)."""
    today = await company_today(s, user.company_id)
    q = select(CallAllocation).where(CallAllocation.company_id == user.company_id, CallAllocation.status == "open")
    if day:
        q = q.where(CallAllocation.run_date == day)
    allocs = list((await s.execute(q)).scalars().all())
    per_caller = (await s.execute(select(User.id, User.full_name, User.status).where(
        User.company_id == user.company_id, User.role == "caller").order_by(User.full_name))).all()
    done_today = dict((await s.execute(select(CallAttempt.caller_id, func.count()).where(
        CallAttempt.company_id == user.company_id, CallAttempt.call_date == today).group_by(CallAttempt.caller_id))).all())
    open_by = {}
    for a in allocs:
        open_by[a.caller_id] = open_by.get(a.caller_id, 0) + 1
    target = (await load_settings(s, user.company_id)).first_attempt_target_days
    entries = {e.id: e for e in (await s.execute(select(SankalpEntry).where(
        SankalpEntry.id.in_([a.entry_id for a in allocs] or [uuid.uuid4()])))).scalars().all()}
    overdue_by: dict = {}
    for a in allocs:
        if a.entry_id in entries and _overdue(entries[a.entry_id], today, target):
            overdue_by[a.caller_id] = overdue_by.get(a.caller_id, 0) + 1
    return {
        "callers": [{"id": str(i), "name": n, "active": st == "active", "open": open_by.get(i, 0),
                     "attempts_today": done_today.get(i, 0), "first_try_overdue": overdue_by.get(i, 0)}
                    for i, n, st in per_caller],
        "unassigned": open_by.get(None, 0),
        "first_try_overdue": sum(overdue_by.values()),
        "items": await _rows_for(s, [a for a in allocs if a.caller_id is None], today),
    }


class AssignIn(BaseModel):
    caller_id: uuid.UUID


@router.post("/calls/allocations/{allocation_id}/assign")
async def assign(allocation_id: uuid.UUID, body: AssignIn, user: User = Depends(require_manage),
                 s: AsyncSession = Depends(get_session)):
    a = await s.get(CallAllocation, allocation_id)
    c = await s.get(User, body.caller_id)
    if not a or a.company_id != user.company_id or a.status != "open":
        raise HTTPException(404, "Not found")
    if not c or c.company_id != user.company_id or c.role != "caller" or c.status != "active":
        raise HTTPException(422, "Pick an active caller")
    a.caller_id = c.id
    audit(s, user, "allocation.assign", "allocation", a.id)
    await s.commit()
    return {"ok": True}


class MoveIn(BaseModel):
    from_caller_id: uuid.UUID
    to_caller_id: uuid.UUID
    # with both: only this many of the branch's new entries not called yet (a caller over the daily limit)
    branch_id: uuid.UUID | None = None
    count: int | None = Field(None, ge=1, le=1000)


@router.post("/calls/allocations/move")
async def move_list(body: MoveIn, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    """A caller is off today: their open list (retries and PRIORITY calls included) goes to another caller.
    The entries keep their first caller, so later retries go back to them."""
    to = await s.get(User, body.to_caller_id)
    if not to or to.company_id != user.company_id or to.role != "caller" or to.status != "active":
        raise HTTPException(422, "Pick an active caller to take the list")
    if body.to_caller_id == body.from_caller_id:
        raise HTTPException(422, "Pick another caller")
    if body.branch_id and body.count:
        # the branch's new entries still waiting for their first call, oldest first; retries keep their first caller
        ids = (await s.execute(select(CallAllocation.id).join(SankalpEntry, SankalpEntry.id == CallAllocation.entry_id).where(
            CallAllocation.company_id == user.company_id, CallAllocation.caller_id == body.from_caller_id,
            CallAllocation.status == "open", CallAllocation.kind == "fresh", SankalpEntry.branch_id == body.branch_id,
            SankalpEntry.last_called_on.is_(None)).order_by(SankalpEntry.submitted_at_device).limit(body.count))).scalars().all()
        if ids:
            await s.execute(CallAllocation.__table__.update().where(CallAllocation.id.in_(ids)).values(caller_id=body.to_caller_id))
        audit(s, user, "allocation.move", "user", body.from_caller_id,
              details={"to": str(body.to_caller_id), "branch": str(body.branch_id), "moved": len(ids)})
        await s.commit()
        return {"moved": len(ids)}
    res = await s.execute(CallAllocation.__table__.update().where(and_(
        CallAllocation.company_id == user.company_id, CallAllocation.caller_id == body.from_caller_id,
        CallAllocation.status == "open")).values(caller_id=body.to_caller_id))
    audit(s, user, "allocation.move", "user", body.from_caller_id,
          details={"to": str(body.to_caller_id), "moved": res.rowcount})
    await s.commit()
    return {"moved": res.rowcount}


# ---------------------------------------------------------------- tracker, green channel, call-centre actions
@router.put("/calls/entries/{entry_id}/tracker")
async def put_tracker(entry_id: uuid.UUID, body: TrackerIn, user: User = Depends(require_manage),
                      s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    await save_tracker(s, e, user, body)
    await s.commit()
    return {**(await calling_detail(s, user, e))["tracker"], "rag": e.rag_override or e.rag, "lead_outcome": e.lead_outcome,
            "tcs_id": e.tcs_id, "priority": e.priority}


@router.get("/calls/tracker")
async def tracker_list(owner: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500),
                       user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    q = (select(FollowupTracker, SankalpEntry).join(SankalpEntry, SankalpEntry.id == FollowupTracker.entry_id)
         .where(FollowupTracker.company_id == user.company_id))
    if owner:
        q = q.where(FollowupTracker.owner == owner)
    total = (await s.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await s.execute(q.order_by(FollowupTracker.followup_date.nulls_last(), SankalpEntry.entry_code)
                            .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [{"entry_id": str(e.id), "entry_code": e.entry_code, "person_name": e.person_name, "owner": t.owner,
                       "action_type": t.action_type, "followup_date": t.followup_date, "outcome": t.outcome,
                       "tcs_id": t.tcs_id, "rag_override": t.rag_override, "notes": t.notes, "status": e.status,
                       "rag": e.rag_override or e.rag} for t, e in rows],
            "total": total, "page": page, "page_size": page_size}


@router.get("/calls/green-channel")
async def green_channel_queue(user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(BranchAnswer, SankalpEntry, User.full_name).join(
        SankalpEntry, SankalpEntry.id == BranchAnswer.entry_id).join(User, User.id == BranchAnswer.answered_by)
        .where(BranchAnswer.company_id == user.company_id, BranchAnswer.green_channel == "pending")
        .order_by(BranchAnswer.created_at))).all()
    cards = {c.entry_id: c for c in (await s.execute(select(LeadCard).where(
        LeadCard.entry_id.in_([e.id for _, e, _ in rows] or [uuid.uuid4()])))).scalars().all()}
    return [{"answer_id": str(a.id), "entry_id": str(e.id), "entry_code": e.entry_code, "person_name": e.person_name,
             "code": a.code, "meaning": R.BRANCH_CODES[a.code][0], "by": n, "responded_on": a.responded_on,
             "loan_requirement": cards[e.id].loan_requirement if e.id in cards else None} for a, e, n in rows]


class GreenChannelIn(BaseModel):
    accept_reject: bool  # False (the rule): not accepted, back to the branch to log in


@router.post("/calls/green-channel/{answer_id}")
async def decide_green_channel(answer_id: uuid.UUID, body: GreenChannelIn, user: User = Depends(require_manage),
                               s: AsyncSession = Depends(get_session)):
    a = await s.get(BranchAnswer, answer_id)
    if not a or a.company_id != user.company_id:
        raise HTTPException(404, "Not found")
    e = await review_green_channel(s, a, user, body.accept_reject)
    await s.commit()
    return {"lead_outcome": e.lead_outcome, "so_action": e.so_action}


@router.get("/calls/actions")
async def cc_actions(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500),
                     user: User = Depends(require_perm("calls.manage")), s: AsyncSession = Depends(get_session)):
    """12.2: callbacks, cases to take forward, follow-ups, by date."""
    q = (select(SankalpEntry, User, Branch, Region).join(User, User.id == SankalpEntry.so_user_id)
         .join(Branch, Branch.id == SankalpEntry.branch_id).outerjoin(Region, Region.id == Branch.region_id)
         .where(SankalpEntry.company_id == user.company_id, SankalpEntry.cc_action.is_not(None)))
    total = (await s.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await s.execute(q.order_by(SankalpEntry.cc_action_date.nulls_last(), SankalpEntry.entry_code)
                            .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [entry_row(*r) for r in rows], "total": total, "page": page, "page_size": page_size}
