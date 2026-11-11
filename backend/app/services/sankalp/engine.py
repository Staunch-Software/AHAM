"""The Sankalp rules as pure functions over plain data (no database), so each rule table is unit-tested directly.

Section numbers refer to "Sankalp app: business logic, from SO entry to lead ID" (v1, 28 Oct 2026).
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.services.sankalp import rules as R


# ---------------------------------------------------------------- 5.2 / 5.3 selection
def is_fresh(*, has_code: bool, selected: bool, call_group: str, entry_date: date, first_call_date: date,
             run_date: date, same_day_calling: bool) -> bool:
    """5.2: an entry is eligible as new when all of these hold."""
    before_run = entry_date <= run_date if same_day_calling else entry_date < run_date
    return has_code and not selected and call_group in ("lead", "dsa_cp") and entry_date >= first_call_date and before_run


def selection_decision(*, call_group: str, phone_valid: bool, repeat_by_same_so: bool, earlier_fresh_same_number: bool,
                       number_in_retry: bool, spoken_within_window: bool, ever_spoken: bool) -> str:
    """5.3, checked in this order. Every "Not called" result is final for that entry."""
    if not phone_valid:
        return R.NC_NO_NUMBER
    if call_group == "lead" and repeat_by_same_so:
        return R.NC_REPEAT
    if earlier_fresh_same_number:
        return R.NC_DUPLICATE
    if number_in_retry:
        return R.NC_BEING_CALLED
    if call_group == "lead" and spoken_within_window:
        return R.NC_SPOKEN
    if call_group == "dsa_cp" and ever_spoken:
        return R.NC_KNOWN
    return R.ALLOCATE


# ---------------------------------------------------------------- 8 classification
def lead_logic(a: dict) -> str:
    """8.1, applied in this order, on the Lead questions of a connected call."""
    need = a.get("loan_need")
    if not need:
        return R.AMBER_MISSING
    if need == R.NO_LOAN:
        return R.RED
    if need in R.LAP_NEEDS:
        return R.NOT_COUNTED_LAP
    if a.get("documents") == "File already logged with Aham":
        return R.ALREADY_IN_PROCESS
    if a.get("relationship") == "Yes – the same officer":
        return R.AMBER_KNOWS_SO
    if (a.get("name_check") or "").startswith("Different person"):
        return R.VALIDATED_DIFFERENT
    if a.get("visit") == "No":
        return R.VALIDATED_NO_VISIT
    return R.VALIDATED


def applicable_answers(a: dict) -> dict:
    """The Lead answers that apply to the loan need (7.2, as the Takeoff call sheet greys the others out)."""
    need = a.get("loan_need")
    out = dict(a)
    if not need or need in R.LAP_NEEDS or need == R.NO_LOAN:
        for k in (*R.LOAN_QUESTIONS, "own_contribution"):
            out.pop(k, None)
    elif need not in R.OWN_CONTRIBUTION_NEEDS:
        out.pop("own_contribution", None)
    return out


def dsa_logic(a: dict) -> str:
    """8.2: a DSA/CP who needs a home loan himself is classified as a lead (converted); otherwise the caller's RAG."""
    if a.get("needs_home_loan") == "Yes":
        st = lead_logic(a)
        return R.VALIDATED_CONVERTED if R.is_validated(st) else st
    return {"Green": R.DSA_GREEN, "NA": R.DSA_NA, "Amber": R.DSA_AMBER, "Red": R.DSA_RED}.get(a.get("dsa_rag") or "", R.DSA_NO_RAG)


def row_status(*, call_group: str, outcome: str, answers: dict | None, unanswered_after: int, max_unanswered: int) -> str:
    """The status one call produces (8.1-8.3). unanswered_after = unanswered tries in this cycle including this one."""
    if outcome == R.CONNECTED:
        return dsa_logic(answers or {}) if call_group == "dsa_cp" else lead_logic(answers or {})
    if outcome == R.INVALID_NUMBER:
        return R.DISCARDED_INVALID
    if outcome == R.WRONG_PERSON:
        return R.AMBER_WRONG_PERSON
    if outcome == R.REFUSED:
        return R.REJECTED_REFUSED
    if outcome == R.CALLBACK:
        return R.CLOSED_NO_ANSWER if call_group == "dsa_cp" else R.IN_RETRY
    # unanswered
    if call_group == "dsa_cp":
        return R.CLOSED_NO_ANSWER
    return R.DISCARDED_9 if unanswered_after >= max_unanswered else R.IN_RETRY


# ---------------------------------------------------------------- state used by the derived fields
@dataclass
class Attempt:
    call_date: date
    outcome: str
    row_status: str | None
    answers: dict | None
    next_date: date | None
    cycle: int
    at: datetime | None = None  # when it was recorded


@dataclass
class BranchAns:
    code: str
    answer_date: date | None
    responded_on: date
    green_channel: str | None = None  # pending | returned (reject not accepted) | accepted
    at: datetime | None = None


@dataclass
class Tracker:
    owner: str | None
    followup_date: date | None
    outcome: str | None
    tcs_id: str | None
    rag_override: str | None
    immediate_callback: bool
    updated_on: date
    action_type: str | None = None
    at: datetime | None = None


@dataclass
class Login:
    tcs_id: str
    login_date: date | None
    product: str | None
    source: str  # register | manual


@dataclass
class EntryState:
    entry_date: date
    call_group: str
    selection_status: str | None
    call_cycle: int
    attempts: list[Attempt] = field(default_factory=list)  # oldest first
    branch_answer: BranchAns | None = None  # the latest
    tracker: Tracker | None = None
    login: Login | None = None
    loan_requirement: int | None = None


@dataclass
class Settings:
    max_unanswered: int = 9
    action_window_days: int = 14
    correct_number_window_days: int = 15
    branch_date_threshold_days: int = 14
    construction_limit: int = 800_000
    purchase_limit: int = 1_500_000


@dataclass
class Derived:
    status: str | None
    unanswered_count: int
    callback_date: date | None
    last_called_on: date | None
    answers: dict | None  # of the latest connected call
    so_action: str | None
    so_action_date: date | None
    so_action_until: date | None
    cc_action: str | None
    cc_action_date: date | None
    lead_outcome: str | None
    rag: str
    rag_override: str | None
    customer_validated: bool
    validated_on: date | None
    green_channel: bool
    priority: bool = False  # called first, every day, until a call gives a status after the reopen (6.2)
    priority_reason: str | None = None
    expired_action: str | None = None  # an action whose window passed unworked (12.3), kept for the expired list
    expired_on: date | None = None


def is_converted(attempts) -> bool:
    """7.3: a DSA/CP contact who said he needs a home loan himself is a lead from then on (works on CallAttempt rows
    and on Attempt)."""
    return any(a.outcome == R.CONNECTED and (a.answers or {}).get("needs_home_loan") == "Yes" for a in attempts)


def current_status(st: EntryState) -> tuple[str | None, int, date | None, date | None, dict | None, Attempt | None,
                                            Attempt | None]:
    """(status, unanswered in this cycle, callback date, last call date, latest connected answers, latest attempt,
    latest call that gave a status).

    The status is the row status of the latest call of the current cycle that gave one (8): connected, invalid
    number, wrong person, refused, or a DSA/CP closed. An unanswered try or a callback request on a lead gives none,
    so a validated lead stays validated when a later follow-up call is not answered (as the Takeoff master does).
    Until a call gives a status the entry is "In retry", or "Discarded – 9 unanswered" after the last allowed try.
    A corrected number starts a new cycle: with no call yet in it, the entry is "In retry" with no tries (13.2)."""
    cur = [a for a in st.attempts if a.cycle == st.call_cycle]
    unanswered = sum(1 for a in cur if a.outcome in R.UNANSWERED)
    last = cur[-1] if cur else None
    giving = [a for a in cur if a.row_status and a.row_status not in R.NO_STATUS_ROWS]
    status_call = giving[-1] if giving else None
    connected = [a for a in cur if a.outcome == R.CONNECTED and a.answers is not None]
    answers = connected[-1].answers if connected else None
    last_called = st.attempts[-1].call_date if st.attempts else None
    if status_call:
        status = status_call.row_status
    elif last:
        status = last.row_status
    else:
        status = R.IN_RETRY if st.call_cycle > 1 else None
    # the callback date: the latest Next date given on a call that did not connect (Takeoff master)
    dates = [a.next_date for a in cur if a.outcome != R.CONNECTED and a.next_date]
    callback = max(dates) if dates and status == R.IN_RETRY else None
    return status, unanswered, callback, last_called, answers, last, status_call


def display_status(*, status: str | None, selection_status: str | None, call_group: str | None,
                   lead_outcome: str | None, unanswered: int = 0, callback_date: date | None = None,
                   priority_reason: str | None = None) -> str:
    """The one current status shown for an entry on every screen and in files: the login outcome when there is one,
    else the latest call's status, else where the entry stands in the selection. Earlier statuses stay in the history."""
    if lead_outcome:
        return lead_outcome
    if status == R.IN_RETRY:
        if priority_reason:
            return f"{R.IN_RETRY} – PRIORITY ({priority_reason})"
        if callback_date:
            return f"{R.IN_RETRY} – call back on {callback_date:%d %b %Y}"
        return f"{R.IN_RETRY} – {unanswered} unanswered" if unanswered else f"{R.IN_RETRY} – not called yet on this number"
    if status:
        return status
    if selection_status and selection_status != R.ALLOCATE:
        return selection_status
    if selection_status == R.ALLOCATE:
        return R.WAITING_FIRST_CALL
    return R.NOT_CALLED_EXISTING if call_group == "none" else R.WAITING_SELECTION


def green_channel(answers: dict | None, loan_requirement: int | None, cfg: Settings) -> bool:
    """12.4: small construction / purchase loans, judged on the call centre's loan requirement."""
    if not answers or loan_requirement is None:
        return False
    need = answers.get("loan_need")
    if need in R.CONSTRUCTION_NEEDS:
        return loan_requirement <= cfg.construction_limit
    if need in R.PURCHASE_NEEDS:
        return loan_requirement <= cfg.purchase_limit
    return False


def lead_outcome(st: EntryState, status: str | None, rejected: bool, lg: Login | None,
                 lead_action: bool = False) -> str | None:
    """11.2, for lead-type entries only (Lead group, converted DSA/CP, or entries carrying a lead action)."""
    lead_type = (st.call_group == "lead" or R.is_validated(status) or status == R.NOT_COUNTED_LAP or lead_action
                 or (st.call_group == "dsa_cp" and is_converted(st.attempts)))
    if not lead_type:
        return None
    if lg and (lg.source == "manual" or (lg.login_date and lg.login_date > st.entry_date)):
        return R.LOGGED_IN
    if rejected:
        return R.OUTCOME_REJECTED
    if lg and lg.source == "register" and (lg.login_date is None or lg.login_date <= st.entry_date):
        return R.LOGIN_BEFORE_ENTRY
    return None


def derive(st: EntryState, cfg: Settings, today: date) -> Derived:
    status, unanswered, callback, last_called, answers, last, status_call = current_status(st)
    ba, tr = st.branch_answer, st.tracker
    # 13.3, as the Takeoff master: the branch answer applies when its response date is on or after the tracker's
    # follow-up date; a tracker row without a follow-up date never overrides a branch answer.
    tracker_wins = bool(tr) and (not ba or (tr.followup_date is not None and tr.followup_date > ba.responded_on))
    branch_wins = bool(ba) and not tracker_wins

    # 6.2, as the Takeoff master: reopened for calling (branch code 3, or the tracker's "Reopen for calling") the entry
    # is "In retry" from the reopen date (the branch's answer, or the tracker's follow-up date, else the day it was
    # saved), with that date as its callback, until a call gives a status on or after it, or the tries run out.
    # Branch code 3 and the master owner's immediate call-back are called first (PRIORITY); a tracker reopen alone
    # comes back as a normal retry. An immediate call-back on its own only puts a not-yet-called entry first.
    reopen_on = reopen_at = reason = None
    if branch_wins and ba.code == "3":
        reopen_on, reopen_at, reason = ba.responded_on, ba.at, "Branch: customer not answering"
    elif tracker_wins and tr.outcome == R.TRACKER_REOPEN:
        reopen_on, reopen_at = tr.followup_date or tr.updated_on, None if tr.followup_date else tr.at
        reason = "Master owner: immediate call-back" if tr.immediate_callback else None
    reopened = False
    if reopen_on and last is not None:
        reached = status_call is not None and (status_call.at >= reopen_at if status_call.at and reopen_at
                                               else status_call.call_date >= reopen_on)
        reopened = not reached and unanswered < cfg.max_unanswered
    if reopened:
        status, callback = R.IN_RETRY, reopen_on
    priority = reopened and reason is not None
    if not priority and tr and tr.immediate_callback and last is None and st.selection_status == R.ALLOCATE:
        priority, reason = True, "Master owner: immediate call-back"

    rejected = False
    if branch_wins and ba.code in R.REJECT_CODES:
        # a green-channel R2/R3 is not accepted until head office agrees ("accepted")
        rejected = ba.green_channel in (None, "accepted")
    if tracker_wins and tr.outcome == "Rejected":
        rejected = True
    login = st.login
    if tr and tr.tcs_id:  # 11.1 manual route: a TCS ID typed by the master owner counts as a login, over the register
        login = Login(tcs_id=tr.tcs_id, login_date=None, product=None, source="manual")
    green_back = (branch_wins and ba.code in R.GREEN_CHANNEL_PROTECTED and ba.green_channel == "returned") or (
        tracker_wins and tr.outcome == R.TRACKER_RETURN_GREEN)
    # a lead action given on the tracker (whatever its owner) makes the entry a lead (Takeoff master)
    tracker_lead_action = tracker_wins and tr.action_type in R.LEAD_ACTIONS
    outcome = lead_outcome(st, status, rejected, login, lead_action=green_back or tracker_lead_action)
    # logged in, rejected, or a login on or before the entry date: nothing more to do (Takeoff master)
    closed = outcome in R.CLOSED_OUTCOMES

    # ---- 12.1 SO / branch action
    so_action = so_date = so_until = None
    cc_action = cc_date = None
    nxt = (answers or {}).get("next_date")
    nxt = date.fromisoformat(nxt) if isinstance(nxt, str) and nxt else None
    call_day = status_call.call_date if status_call else (last.call_date if last else None)
    if not closed:
        if status in (R.AMBER_WRONG_PERSON, R.DISCARDED_INVALID) or st.selection_status == R.NC_NO_NUMBER:
            so_action, so_date = R.ACT_CORRECT_NUMBER, call_day or st.entry_date
            so_until = so_date + timedelta(days=cfg.correct_number_window_days)  # from that call (Takeoff master)
        elif status == R.DSA_GREEN:
            so_action, so_date = R.ACT_DSA_FOLLOWUP, call_day
            so_until = (call_day or today) + timedelta(days=cfg.action_window_days)
        elif R.is_validated(status) or status == R.NOT_COUNTED_LAP:
            step = (answers or {}).get("next_step")
            if step == "SO / branch visit":
                so_action, so_date = R.ACT_VISIT, nxt or call_day
            elif step == "Call centre to continue":
                cc_action, cc_date = R.CC_TAKE_FORWARD, nxt or call_day
            elif (answers or {}).get("documents") in ("Partly", "No"):
                so_action, so_date = R.ACT_COLLECT_DOCS, call_day
            else:
                so_action, so_date = R.ACT_FOLLOW_UP_LEAD, call_day
            # lead actions stay open until login or rejection (so_until stays None)

        # ---- branch answer (12.4): the date it gives moves the lead's action; 14-day rule
        if branch_wins and so_action in R.LEAD_ACTIONS and ba.answer_date:
            if ba.answer_date > ba.responded_on + timedelta(days=cfg.branch_date_threshold_days):
                # the call centre follows up on that date; once it has called, the lead is the branch's again
                if not (last_called and last_called >= ba.answer_date):
                    cc_action, cc_date = R.CC_FOLLOW_UP, ba.answer_date
                    so_action = so_date = None
            else:
                so_date = ba.answer_date
        # ---- green channel (12.4): a reject the head office did not accept goes back to the branch to log in
        if green_back:
            so_action, so_until = R.ACT_GREEN_LOGIN, None
            so_date = ba.responded_on if branch_wins else (tr.followup_date or tr.updated_on)
        # ---- tracker (13.3), as the Takeoff master: the owner decides whose list shows the entry
        if tracker_wins and tr.owner == "branch" and not green_back:
            # the master owner gives the branch an action and a date; it stays until the tracker changes
            so_action, so_until = tr.action_type or R.ACT_BRANCH_FOLLOWUP, None
            so_date, cc_action, cc_date = tr.followup_date or st.entry_date, None, None
        if tracker_wins and tr.owner == "call_centre":
            # sent to the call centre: a follow-up on its date, done once the call centre has called (from then on)
            due = tr.followup_date or tr.updated_on
            done = last_called is not None and (last_called >= tr.followup_date if tr.followup_date else last_called > tr.updated_on)
            if not done:
                cc_action, cc_date, so_action, so_date, so_until = R.CC_FOLLOW_UP, due, None, None, None
        if tracker_wins and tr.owner == "done":
            so_action = so_date = so_until = cc_action = cc_date = None
        # ---- 12.2 callback (none while the tracker gives the entry to an owner)
        if status == R.IN_RETRY and callback and not (tracker_wins and tr.owner):
            cc_action, cc_date = R.CC_CALLBACK, callback

    # 12.3: lead actions stay open until login or rejection; "correct number" for 15 days from its call; a DSA/CP
    # follow-up for 14 days. On the call-centre side only a callback runs out (14 days after its date): a case taken
    # forward and a follow-up stay until done, as in the Takeoff master. Expired actions are not "open".
    so_open = so_action is not None and (so_until is None or so_until >= today)
    cc_open = cc_action is not None and (cc_action != R.CC_CALLBACK or cc_date is None
                                         or cc_date + timedelta(days=cfg.action_window_days) >= today)
    expired_action = expired_on = None
    if so_action is not None and not so_open:
        expired_action, expired_on = so_action, so_until
    elif cc_action is not None and not cc_open:
        expired_action, expired_on = cc_action, cc_date + timedelta(days=cfg.action_window_days)
    validating = [a for a in st.attempts if R.is_validated(a.row_status)]
    rag = rag_for(status=status, selection_status=st.selection_status, unanswered=unanswered, lead_outcome=outcome,
                  has_open_action=so_open or cc_open, call_group=st.call_group,
                  lost_lead=status == R.RED and bool(validating))
    override = tr.rag_override if tr and tr.rag_override else None
    lap = status == R.NOT_COUNTED_LAP or bool(login and login.product and "LAP" in login.product.upper())
    repeat = st.selection_status == R.NC_REPEAT
    validated = (R.is_validated(status) or (outcome == R.LOGGED_IN and not lap)) and not repeat
    # 10: the date of the latest call that gave a status (the Takeoff master); none for a login without such a call
    validated_on = status_call.call_date if validated and status_call else None
    return Derived(
        status=status, unanswered_count=unanswered, callback_date=callback, last_called_on=last_called, answers=answers,
        so_action=so_action if so_open else None, so_action_date=so_date if so_open else None,
        so_action_until=so_until if so_open else None,
        cc_action=cc_action if cc_open else None, cc_action_date=cc_date if cc_open else None,
        lead_outcome=outcome, rag=rag, rag_override=override, customer_validated=validated, validated_on=validated_on,
        green_channel=green_channel(answers, st.loan_requirement, cfg),
        expired_action=expired_action, expired_on=expired_on,
        priority=priority and not closed, priority_reason=reason if priority and not closed else None,
    )


# ---------------------------------------------------------------- 9 RAG
def rag_for(*, status: str | None, selection_status: str | None, unanswered: int, lead_outcome: str | None,
            has_open_action: bool, call_group: str | None = None, lost_lead: bool = False) -> str:
    """Section 9 (a manual override by the master owner is applied on top, by the caller).

    lost_lead: Red on a lead an earlier call had validated (the need has passed); section 9 makes a lost lead NA."""
    if lead_outcome in R.CLOSED_OUTCOMES:
        return "NA"
    if call_group == "none":
        return "NA"  # Existing Customer / Applicant: not called (5.1), so never "waiting to be called"
    if selection_status and selection_status != R.ALLOCATE and status is None:
        return "AMBER" if selection_status == R.NC_NO_NUMBER else "NA"
    if status is None:
        return "PENDING"
    if status in (R.RED, R.DSA_RED):
        return "NA" if lost_lead and status == R.RED else "RED"
    if status.startswith("Amber") or status in (R.DSA_AMBER, R.DISCARDED_INVALID):
        return "AMBER"
    if status == R.IN_RETRY:
        return "RNR" if unanswered > 0 else "GREEN"
    if status.startswith("Discarded") or status == R.CLOSED_NO_ANSWER:
        return "RNR"
    if status == R.DSA_GREEN:
        return "GREEN"
    if status == R.DSA_NA:
        return "NA"
    if has_open_action:
        return "GREEN"
    return "NA"


# ---------------------------------------------------------------- 11.3 success, 10 first validation
def sankalp_success_winner(candidates: list[tuple[date, str, str, bool]], takeoff_start: date) -> str | None:
    """candidates: (entry_date, entry_code, entry_id, logged_in) of every entry carrying one TCS ID.
    As the Takeoff master: the earliest logged-in entry wins (ties: lower Entry ID), if dated on or after Takeoff
    start. An entry whose login was on or before its own date does not compete."""
    logged = [c for c in candidates if c[3]]
    if not logged:
        return None
    entry_date, _, entry_id, _ = min(logged, key=lambda c: (c[0], c[1]))
    return entry_id if entry_date >= takeoff_start else None


def first_validated(candidates: list[tuple[str, str, bool]]) -> str | None:
    """candidates: (sort key, entry id, validated) of every entry with one phone number; the sort key orders entries
    by when they were made. Returns the id of the earliest validated entry: paid once per customer (section 10)."""
    vals = sorted((k, i) for k, i, v in candidates if v)
    return vals[0][1] if vals else None


# ---------------------------------------------------------------- 7 attempt limits
def attempt_allowed(*, call_group: str, attempts_today: int, days_called: set[date], today: date, cfg_tries_lead: int,
                    cfg_max_slots: int, cfg_tries_dsa: int) -> str | None:
    """Returns a reason when no further attempt may be recorded today, else None. call_group is the group whose
    calling rules apply (a converted DSA/CP is called as a lead)."""
    if call_group == "dsa_cp":
        # one calling day only: a callback request closes a DSA/CP like an unanswered try (Takeoff master)
        if days_called and today not in days_called:
            return "A DSA/CP entry is called on one day only"
        if attempts_today >= cfg_tries_dsa:
            return f"A DSA/CP entry gets {cfg_tries_dsa} try a day"
        return None
    if attempts_today >= cfg_max_slots:
        return f"Up to {cfg_max_slots} attempts can be recorded per entry per day"
    return None
