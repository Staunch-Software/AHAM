"""Call-centre portal (sections 5-8, 13.3): the daily run, callers' lists, recording calls, the lead card, the tracker."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_perm
from app.api.v1.entries import entry_row, get_scoped_entry
from app.core.db import get_session
from app.models import (
    Branch,
    BranchAnswer,
    CallAllocation,
    CallAttempt,
    CallerDay,
    FollowupTracker,
    LeadCard,
    Region,
    SankalpEntry,
    SelectionRun,
    User,
)
from app.services.reference import audit
from app.services.sankalp import rules as R
from app.services.sankalp.handoff import review_green_channel, save_tracker
from app.services.sankalp.ops import company_today, record_attempt, run_selection, save_lead_card
from app.services.sankalp.schemas import AttemptIn, LeadCardIn, TrackerIn
from app.services.sankalp.views import calling_detail
from app.services.settings import load_settings

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
        "tracker": {"owners": R.TRACKER_OWNERS, "outcomes": R.TRACKER_OUTCOMES},
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
    return {"today": today, "items": await _rows_for(s, list(allocs), today)}


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
    return {"day": day, "items": [{"branch_id": str(b.id), "branch": b.name, "region": rn,
                                   "caller_id": str(rows[b.id]) if b.id in rows else None} for b, rn in branches]}


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


@router.post("/calls/allocations/move")
async def move_list(body: MoveIn, user: User = Depends(require_manage), s: AsyncSession = Depends(get_session)):
    """A caller is off today: their open list (retries and PRIORITY calls included) goes to another caller.
    The entries keep their first caller, so later retries go back to them."""
    to = await s.get(User, body.to_caller_id)
    if not to or to.company_id != user.company_id or to.role != "caller" or to.status != "active":
        raise HTTPException(422, "Pick an active caller to take the list")
    if body.to_caller_id == body.from_caller_id:
        raise HTTPException(422, "Pick another caller")
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
