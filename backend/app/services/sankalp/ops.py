"""Database side of the Sankalp flow: the daily selection run (5), allocation (6), recording calls (7-8), and
recompute() which refreshes an entry's derived fields (status, RAG, actions, lead outcome, flags) after any event."""
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Branch,
    BranchAnswer,
    CallAllocation,
    CallAttempt,
    CallerDay,
    Company,
    EntryEvent,
    FollowupTracker,
    ImportBatch,
    LeadCard,
    LoginRegisterRow,
    SankalpEntry,
    SelectionRun,
    User,
)
from app.services.periods import today_local, tz_of
from app.services.phone import is_valid_phone
from app.services.sankalp import engine as E
from app.services.sankalp import rules as R
from app.services.sankalp.schemas import AttemptIn, LeadCardIn
from app.services.settings import SankalpSettings, load_settings


def engine_settings(cfg: SankalpSettings) -> E.Settings:
    return E.Settings(max_unanswered=cfg.max_unanswered_lead, action_window_days=cfg.action_window_days,
                      correct_number_window_days=cfg.correct_number_window_days,
                      branch_date_threshold_days=cfg.branch_date_threshold_days,
                      construction_limit=cfg.green_channel_construction_limit,
                      purchase_limit=cfg.green_channel_purchase_limit)


async def company_today(s: AsyncSession, company_id: uuid.UUID) -> date:
    return today_local(tz_of((await s.get(Company, company_id)).timezone))


def event(s: AsyncSession, e: SankalpEntry, kind: str, actor_id: uuid.UUID | None, **detail) -> None:
    s.add(EntryEvent(entry_id=e.id, company_id=e.company_id, kind=kind, actor_id=actor_id,
                     detail={k: (str(v) if isinstance(v, (date, uuid.UUID)) else v) for k, v in detail.items()} or None))


# ================================================================ login register (11.1)
async def best_login(s: AsyncSession, company_id: uuid.UUID, phone: str, entry_date: date, rule: str) -> E.Login | None:
    """The register login matching this phone. For a TCS ID that appears more than once, one row wins (the latest
    by default; setting duplicate_tcs_rule). A login after the entry date is preferred over one on or before it."""
    hits = (await s.execute(select(LoginRegisterRow.tcs_id).where(
        LoginRegisterRow.company_id == company_id, LoginRegisterRow.phones.contains([phone])).distinct())).scalars().all()
    if not hits:
        return None
    rows = (await s.execute(
        select(LoginRegisterRow).join(ImportBatch, ImportBatch.id == LoginRegisterRow.batch_id)
        .where(LoginRegisterRow.company_id == company_id, LoginRegisterRow.tcs_id.in_(hits))
        .order_by(ImportBatch.created_at, LoginRegisterRow.row_no))).scalars().all()
    effective: dict[str, LoginRegisterRow] = {}
    for r in rows:
        if rule == "latest" or r.tcs_id not in effective:
            effective[r.tcs_id] = r
    logins = [E.Login(tcs_id=r.tcs_id, login_date=r.login_date, product=r.product, source="register")
              for r in effective.values() if phone in (r.phones or [])]
    after = sorted((lg for lg in logins if lg.login_date and lg.login_date > entry_date), key=lambda lg: lg.login_date)
    if after:
        return after[0]
    return max(logins, key=lambda lg: lg.login_date or date.min, default=None)


# ================================================================ recompute
async def load_state(s: AsyncSession, e: SankalpEntry, cfg: SankalpSettings) -> E.EntryState:
    attempts = (await s.execute(select(CallAttempt).where(CallAttempt.entry_id == e.id)
                                .order_by(CallAttempt.created_at, CallAttempt.id))).scalars().all()
    ba = (await s.execute(select(BranchAnswer).where(BranchAnswer.entry_id == e.id)
                          .order_by(BranchAnswer.created_at.desc()).limit(1))).scalar_one_or_none()
    tr = await s.get(FollowupTracker, e.id)
    card = await s.get(LeadCard, e.id)
    return E.EntryState(
        entry_date=e.entry_date, call_group=e.call_group, selection_status=e.selection_status, call_cycle=e.call_cycle,
        attempts=[E.Attempt(a.call_date, a.outcome, a.row_status, a.answers, a.next_date, a.cycle) for a in attempts],
        branch_answer=E.BranchAns(ba.code, ba.answer_date, ba.responded_on, ba.green_channel) if ba else None,
        tracker=E.Tracker(tr.owner, tr.followup_date, tr.outcome, tr.tcs_id, tr.rag_override, tr.immediate_callback,
                          tr.updated_at.date()) if tr else None,
        login=await best_login(s, e.company_id, e.phone, e.entry_date, cfg.duplicate_tcs_rule),
        loan_requirement=card.loan_requirement if card else None,
    )


async def recompute(s: AsyncSession, e: SankalpEntry, *, cfg: SankalpSettings | None = None, today: date | None = None,
                    groups: bool = True) -> E.Derived:
    """Refresh every derived field of one entry, then the flags that depend on other entries with the same phone
    (first validation) and the same TCS ID (Sankalp success)."""
    cfg = cfg or await load_settings(s, e.company_id)
    today = today or await company_today(s, e.company_id)
    st = await load_state(s, e, cfg)
    d = E.derive(st, engine_settings(cfg), today)
    if d.status != e.status:
        e.status_at = datetime.now(timezone.utc)
    old_tcs = e.tcs_id
    e.status, e.unanswered_count, e.callback_date, e.last_called_on = d.status, d.unanswered_count, d.callback_date, d.last_called_on
    e.so_action, e.so_action_date, e.so_action_until = d.so_action, d.so_action_date, d.so_action_until
    e.cc_action, e.cc_action_date = d.cc_action, d.cc_action_date
    e.lead_outcome, e.rag, e.rag_override = d.lead_outcome, d.rag, d.rag_override
    e.customer_validated, e.validated_on = d.customer_validated, d.validated_on
    if d.expired_action and d.expired_action != e.expired_action:
        event(s, e, "action.expired", None, action=d.expired_action, on=d.expired_on)
    e.expired_action, e.expired_on = d.expired_action, d.expired_on
    tr = st.tracker
    login = st.login or (E.Login(tr.tcs_id, None, None, "manual") if tr and tr.tcs_id else None)
    e.tcs_id = login.tcs_id if login else None
    e.login_date = login.login_date if login else None
    e.login_source = login.source if login else None
    if not e.tcs_id:
        e.sankalp_success = False  # success belongs to a TCS ID (11.3)
    await s.flush()
    if groups:
        await recompute_phone_group(s, e.company_id, e.phone)
        for tcs in {old_tcs, e.tcs_id} - {None}:
            await recompute_tcs_group(s, e.company_id, tcs, cfg.takeoff_start)
    return d


async def recompute_phone_group(s: AsyncSession, company_id: uuid.UUID, phone: str) -> None:
    """Section 10: "first validation for this number" goes to the earliest validated entry, from any SO."""
    rows = (await s.execute(select(SankalpEntry).where(SankalpEntry.company_id == company_id,
                                                       SankalpEntry.phone == phone))).scalars().all()
    winner = E.first_validated([(f"{r.submitted_at_device.isoformat()}|{r.entry_code}", str(r.id), r.customer_validated)
                                for r in rows])
    for r in rows:
        r.first_validation = str(r.id) == winner


async def recompute_tcs_group(s: AsyncSession, company_id: uuid.UUID, tcs_id: str, takeoff_start: date) -> None:
    """11.3: one Sankalp success per TCS ID: the earliest entry, if it logged in on or after Takeoff start."""
    rows = (await s.execute(select(SankalpEntry).where(SankalpEntry.company_id == company_id,
                                                       SankalpEntry.tcs_id == tcs_id))).scalars().all()
    winner = E.sankalp_success_winner([(r.entry_date, r.entry_code, str(r.id), r.lead_outcome == R.LOGGED_IN) for r in rows],
                                      takeoff_start)
    for r in rows:
        r.sankalp_success = str(r.id) == winner


async def recompute_many(s: AsyncSession, company_id: uuid.UUID, where, cfg: SankalpSettings | None = None) -> int:
    cfg = cfg or await load_settings(s, company_id)
    today = await company_today(s, company_id)
    rows = (await s.execute(select(SankalpEntry).where(SankalpEntry.company_id == company_id, where))).scalars().all()
    for e in rows:
        await recompute(s, e, cfg=cfg, today=today)
    return len(rows)


async def recompute_time_based(s: AsyncSession, company_id: uuid.UUID) -> int:
    """Daily: actions whose window has passed close, which can change the RAG (12.3)."""
    today = await company_today(s, company_id)
    cfg = await load_settings(s, company_id)
    return await recompute_many(s, company_id, or_(
        SankalpEntry.so_action_until < today,
        SankalpEntry.cc_action_date < today - timedelta(days=cfg.action_window_days)), cfg)


# ================================================================ 5 selection + 6 allocation
async def run_selection(s: AsyncSession, company_id: uuid.UUID, run_date: date, actor: User | None) -> dict:
    """The daily run for a run date: decide every fresh entry (5.3, in timestamp order, earliest wins), then put
    today's work on the callers' lists (6). Safe to run again the same day: it only adds what is missing."""
    await s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"selection:{company_id}"})
    cfg = await load_settings(s, company_id)
    win = cfg.repeat_window_days
    # 6: work not recorded before this run is offered again (re-derived below from the entries' state)
    stale = await s.execute(update(CallAllocation).where(CallAllocation.company_id == company_id,
                                                         CallAllocation.status == "open", CallAllocation.run_date < run_date)
                            .values(status="unreturned", closed_at=datetime.now(timezone.utc)))
    # ---- 5: fresh entries
    cond = [SankalpEntry.company_id == company_id, SankalpEntry.selection_status.is_(None),
            SankalpEntry.call_group.in_(["lead", "dsa_cp"]), SankalpEntry.entry_date >= cfg.first_call_date,
            SankalpEntry.entry_date <= run_date if cfg.same_day_calling else SankalpEntry.entry_date < run_date]
    fresh = (await s.execute(select(SankalpEntry).where(*cond)
                             .order_by(SankalpEntry.submitted_at_device, SankalpEntry.entry_code))).scalars().all()
    phones = {e.phone for e in fresh}
    others = (await s.execute(select(SankalpEntry).where(
        SankalpEntry.company_id == company_id, SankalpEntry.phone.in_(phones or {""}),
        SankalpEntry.selection_status.is_not(None)))).scalars().all() if phones else []
    by_phone: dict[str, list[SankalpEntry]] = defaultdict(list)
    for o in [*others, *fresh]:
        by_phone[o.phone].append(o)
    # "being called": allocated and not finished (waiting for a first call, or in retry)
    being_called = {o.phone for o in others if o.selection_status == R.ALLOCATE and o.status in (None, R.IN_RETRY)}
    spoken = dict((await s.execute(
        select(SankalpEntry.phone, func.max(CallAttempt.call_date)).join(CallAttempt, CallAttempt.entry_id == SankalpEntry.id)
        .where(SankalpEntry.company_id == company_id, SankalpEntry.phone.in_(phones or {""}),
               CallAttempt.outcome == R.CONNECTED).group_by(SankalpEntry.phone))).all()) if phones else {}
    counts: dict[str, int] = defaultdict(int)
    seen_fresh: set[str] = set()
    selected_now: list[SankalpEntry] = []
    for e in fresh:
        repeat = any(o.id != e.id and o.so_user_id == e.so_user_id and o.submitted_at_device < e.submitted_at_device
                     and timedelta(0) <= e.entry_date - o.entry_date <= timedelta(days=win) for o in by_phone[e.phone])
        last_spoken = spoken.get(e.phone)
        decision = E.selection_decision(
            call_group=e.call_group, phone_valid=is_valid_phone(e.phone), repeat_by_same_so=repeat,
            earlier_fresh_same_number=e.phone in seen_fresh, number_in_retry=e.phone in being_called,
            spoken_within_window=bool(last_spoken and last_spoken >= run_date - timedelta(days=win)),
            ever_spoken=last_spoken is not None)
        seen_fresh.add(e.phone)
        e.selection_status, e.selection_run_on = decision, run_date
        counts[decision] += 1
        event(s, e, "selection", actor.id if actor else None, result=decision, run_date=run_date)
        if decision == R.ALLOCATE:
            being_called.add(e.phone)
            selected_now.append(e)
        await recompute(s, e, cfg=cfg, today=run_date, groups=False)
    alloc = await allocate(s, company_id, run_date)
    run = SelectionRun(company_id=company_id, run_date=run_date, started_by=actor.id if actor else None,
                       counts={"selection": dict(counts), "allocated": alloc, "unreturned": stale.rowcount})
    s.add(run)
    await recompute_time_based(s, company_id)
    return {"run_date": run_date, "selection": dict(counts), "allocated": alloc, "unreturned": stale.rowcount}


async def caller_of_day(s: AsyncSession, company_id: uuid.UUID, day: date) -> dict[uuid.UUID, uuid.UUID]:
    rows = (await s.execute(select(CallerDay.branch_id, CallerDay.caller_id).where(
        CallerDay.company_id == company_id, CallerDay.day == day))).all()
    return dict(rows)


async def allocate(s: AsyncSession, company_id: uuid.UUID, run_date: date) -> dict:
    """Section 6. New entries go to their branch's caller of the day; retries, priority and follow-ups to the caller
    who first handled the entry. Entries already on a list today are left alone."""
    branch_caller = await caller_of_day(s, company_id, run_date)
    active_callers = set((await s.execute(select(User.id).where(User.company_id == company_id, User.role == "caller",
                                                                User.status == "active"))).scalars().all())
    already = set((await s.execute(select(CallAllocation.entry_id).where(
        CallAllocation.company_id == company_id, CallAllocation.status == "open"))).scalars().all())
    trackers = dict((await s.execute(select(FollowupTracker.entry_id, FollowupTracker.caller_id).where(
        FollowupTracker.company_id == company_id, FollowupTracker.caller_id.is_not(None)))).all())
    not_closed = or_(SankalpEntry.lead_outcome.is_(None), SankalpEntry.lead_outcome.notin_([R.LOGGED_IN, R.OUTCOME_REJECTED]))
    not_today = or_(SankalpEntry.last_called_on.is_(None), SankalpEntry.last_called_on < run_date)
    base = [SankalpEntry.company_id == company_id, not_closed, not_today]
    queries = {
        "priority": and_(SankalpEntry.priority),
        "retry": and_(SankalpEntry.status == R.IN_RETRY,
                      or_(SankalpEntry.callback_date.is_(None), SankalpEntry.callback_date <= run_date)),
        "followup": and_(SankalpEntry.cc_action.in_([R.CC_TAKE_FORWARD, R.CC_FOLLOW_UP]),
                         SankalpEntry.cc_action_date <= run_date),
        "fresh": and_(SankalpEntry.selection_status == R.ALLOCATE, SankalpEntry.status.is_(None),
                      SankalpEntry.last_called_on.is_(None)),
    }
    made: dict[str, int] = defaultdict(int)
    for kind, cond in queries.items():  # in priority order: an entry gets one allocation, of the first kind it fits
        rows = (await s.execute(select(SankalpEntry).where(*base, cond)
                                .order_by(SankalpEntry.submitted_at_device, SankalpEntry.entry_code))).scalars().all()
        for e in rows:
            if e.id in already:
                continue
            if kind == "fresh":
                caller = branch_caller.get(e.branch_id)
            else:
                caller = trackers.get(e.id) or e.first_caller_id
                if caller not in active_callers:
                    caller = branch_caller.get(e.branch_id)
            s.add(CallAllocation(company_id=company_id, entry_id=e.id, caller_id=caller, run_date=run_date, kind=kind))
            already.add(e.id)
            made[kind] += 1
            if caller is None:
                made["unassigned"] += 1
    await s.flush()
    return dict(made)


# ================================================================ 7 recording a call
async def record_attempt(s: AsyncSession, e: SankalpEntry, user: User, body: AttemptIn) -> CallAttempt:
    cfg = await load_settings(s, e.company_id)
    today = await company_today(s, e.company_id)
    if e.lead_outcome == R.LOGGED_IN:
        raise HTTPException(409, {"code": "logged_in", "message": "This lead has logged in; it is not called again"})
    mine = (await s.execute(select(CallAllocation).where(CallAllocation.entry_id == e.id, CallAllocation.status == "open")
                            )).scalars().all()
    if user.role == "caller" and not any(a.caller_id == user.id for a in mine):
        raise HTTPException(403, {"code": "not_on_your_list", "message": "This entry is not on your calling list"})
    if not mine and e.selection_status != R.ALLOCATE:
        raise HTTPException(409, {"code": "not_callable", "message": f"This entry is '{e.selection_status or 'not selected'}' and is not called"})
    attempts = (await s.execute(select(CallAttempt).where(CallAttempt.entry_id == e.id))).scalars().all()
    # A DSA/CP contact who needs a home loan himself is called as a lead from then on (7.3).
    converted = e.call_group == "dsa_cp" and E.is_converted(attempts)
    rules_group = "lead" if converted else e.call_group
    reason = E.attempt_allowed(call_group=rules_group, attempts_today=sum(1 for a in attempts if a.call_date == today),
                               days_called={a.call_date for a in attempts}, today=today,
                               cfg_tries_lead=cfg.tries_per_day_lead, cfg_max_slots=cfg.max_slots_per_day,
                               cfg_tries_dsa=cfg.tries_per_day_dsa,
                               callback_days={a.next_date for a in attempts if a.outcome == R.CALLBACK and a.next_date
                                              and a.cycle == e.call_cycle})
    if reason and not e.priority:
        raise HTTPException(409, {"code": "attempt_limit", "message": reason})
    if body.next_date and body.next_date < today:
        raise HTTPException(422, {"code": "date_in_past", "message": "The callback date is in the past"})
    answers = body.answers.model_dump(mode="json", exclude_none=True) if body.answers else None
    if body.outcome == R.CONNECTED and e.call_group == "lead" and answers:
        answers.pop("dsa_rag", None)
        answers.pop("needs_home_loan", None)
    if body.outcome == R.CONNECTED and answers is None:
        answers = {}
    if body.outcome == R.CONNECTED and converted:
        answers.setdefault("needs_home_loan", "Yes")  # a later call keeps the conversion unless the caller changes it
    unanswered_now = sum(1 for a in attempts if a.cycle == e.call_cycle and a.outcome in R.UNANSWERED)
    unanswered_after = unanswered_now + (1 if body.outcome in R.UNANSWERED else 0)
    row = E.row_status(call_group=e.call_group if body.outcome == R.CONNECTED else rules_group, outcome=body.outcome,
                       answers=answers, unanswered_after=unanswered_after, max_unanswered=cfg.max_unanswered_lead)
    a = CallAttempt(company_id=e.company_id, entry_id=e.id, caller_id=user.id, call_date=today, slot=body.slot,
                    outcome=body.outcome, cycle=e.call_cycle, next_date=body.next_date, answers=answers, row_status=row)
    s.add(a)
    if e.first_caller_id is None and user.role == "caller":
        e.first_caller_id = user.id
    e.priority, e.priority_reason = False, None
    await s.flush()
    # The entry leaves today's list once the call is final, a callback is set, or today's tries are used up.
    tries_today = sum(1 for x in attempts if x.call_date == today) + 1
    per_day = cfg.tries_per_day_dsa if rules_group == "dsa_cp" else cfg.tries_per_day_lead
    if row != R.IN_RETRY or body.outcome == R.CALLBACK or tries_today >= per_day:
        for al in mine:
            al.status, al.closed_at = "done", datetime.now(timezone.utc)
    event(s, e, "call", user.id, slot=body.slot, outcome=body.outcome, status=row)
    await recompute(s, e, cfg=cfg, today=today)
    return a


async def save_lead_card(s: AsyncSession, e: SankalpEntry, user: User, body: LeadCardIn) -> LeadCard:
    """7.4: the card opens once Loan need shows a loan type. The lead ID never closes a lead (it is not a login)."""
    last = (await s.execute(select(CallAttempt).where(CallAttempt.entry_id == e.id, CallAttempt.outcome == R.CONNECTED)
                            .order_by(CallAttempt.created_at.desc()).limit(1))).scalar_one_or_none()
    need = (last.answers or {}).get("loan_need") if last else None
    if not need or need == R.NO_LOAN:
        raise HTTPException(409, {"code": "no_loan_need", "message": "The lead card opens once Loan need shows a loan type"})
    if body.handling_branch_id:
        b = await s.get(Branch, body.handling_branch_id)
        if not b or b.company_id != e.company_id:
            raise HTTPException(404, "Handling branch not found")
    card = await s.get(LeadCard, e.id)
    if card is None:
        card = LeadCard(entry_id=e.id, company_id=e.company_id, data={})
        s.add(card)
    had_lead_id = card.lead_id
    data = body.model_dump(mode="json", exclude={"handling_branch_id", "loan_requirement", "lead_id"}, exclude_none=True)
    before = {**(card.data or {}), "handling_branch_id": str(card.handling_branch_id) if card.handling_branch_id else None,
              "loan_requirement": card.loan_requirement}
    after = {**data, "handling_branch_id": str(body.handling_branch_id) if body.handling_branch_id else None,
             "loan_requirement": body.loan_requirement}
    changes = {k: [before.get(k), after.get(k)] for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)}
    card.data, card.handling_branch_id = data, body.handling_branch_id
    card.loan_requirement, card.lead_id, card.updated_by = body.loan_requirement, body.lead_id, user.id
    # 7.4: another branch works the lead when the property is in its area; credit stays with the SO's branch
    e.work_branch_id = body.handling_branch_id if body.handling_branch_id and body.handling_branch_id != e.branch_id else None
    if changes:
        event(s, e, "lead_card", user.id, changes=changes)
    if body.lead_id and body.lead_id != had_lead_id:
        card.lead_id_at = datetime.now(timezone.utc)
        event(s, e, "lead_id", user.id, lead_id=body.lead_id)
    await s.flush()
    await recompute(s, e)
    return card
