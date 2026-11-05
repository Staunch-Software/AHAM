"""The Sankalp rules as pure functions over plain data (no database), so each rule table is unit-tested directly.

Section numbers refer to "Sankalp app: business logic, from SO entry to lead ID" (v1, 28 Oct 2026).
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

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
        return R.IN_RETRY
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


@dataclass
class BranchAns:
    code: str
    answer_date: date | None
    responded_on: date
    green_channel: str | None = None  # pending | returned (reject not accepted) | accepted


@dataclass
class Tracker:
    owner: str | None
    followup_date: date | None
    outcome: str | None
    tcs_id: str | None
    rag_override: str | None
    immediate_callback: bool
    updated_on: date


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
    expired_action: str | None = None  # an action whose window passed unworked (12.3), kept for the expired list
    expired_on: date | None = None


def is_converted(attempts) -> bool:
    """7.3: a DSA/CP contact who said he needs a home loan himself is a lead from then on (works on CallAttempt rows
    and on Attempt)."""
    return any(a.outcome == R.CONNECTED and (a.answers or {}).get("needs_home_loan") == "Yes" for a in attempts)


def current_status(st: EntryState) -> tuple[str | None, int, date | None, date | None, dict | None, Attempt | None]:
    """(status, unanswered in this cycle, callback date, last call date, latest connected answers, latest attempt).

    The status is the row status of the latest call of the current cycle. A corrected number starts a new cycle:
    with no call yet in it, the entry is "In retry" with no tries (13.2)."""
    cur = [a for a in st.attempts if a.cycle == st.call_cycle]
    unanswered = sum(1 for a in cur if a.outcome in R.UNANSWERED)
    last = cur[-1] if cur else None
    connected = [a for a in cur if a.outcome == R.CONNECTED and a.answers is not None]
    answers = connected[-1].answers if connected else None
    last_called = st.attempts[-1].call_date if st.attempts else None
    if last:
        status = last.row_status
        callback = last.next_date if last.outcome == R.CALLBACK else None
    else:
        status = R.IN_RETRY if st.call_cycle > 1 else None
        callback = None
    return status, unanswered, callback, last_called, answers, last


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


def lead_outcome(st: EntryState, status: str | None, rejected: bool, lg: Login | None) -> str | None:
    """11.2, for lead-type entries only (Lead group, converted DSA/CP, or entries carrying a lead action)."""
    lead_type = (st.call_group == "lead" or R.is_validated(status) or status == R.NOT_COUNTED_LAP
                 or (st.call_group == "dsa_cp" and is_converted(st.attempts)))
    if not lead_type:
        return None
    if lg and (lg.source == "manual" or (lg.login_date and lg.login_date > st.entry_date)):
        return R.LOGGED_IN
    if rejected:
        return R.OUTCOME_REJECTED
    if lg and lg.login_date and lg.login_date <= st.entry_date:
        return R.LOGIN_BEFORE_ENTRY
    return None


def derive(st: EntryState, cfg: Settings, today: date) -> Derived:
    status, unanswered, callback, last_called, answers, last = current_status(st)
    ba, tr = st.branch_answer, st.tracker
    # 13.3: where an entry has both a tracker row and a branch answer, the one with the later date applies
    # (tracker: follow-up date, else the day it was saved; branch: response date).
    tracker_wins = bool(tr) and (not ba or (tr.followup_date or tr.updated_on) >= ba.responded_on)
    branch_wins = bool(ba) and not tracker_wins

    rejected = False
    if branch_wins and ba.code in R.REJECT_CODES:
        # a green-channel R2/R3 is not accepted until head office agrees ("accepted")
        rejected = ba.green_channel in (None, "accepted")
    if tracker_wins and tr.outcome == "Rejected":
        rejected = True
    login = st.login
    if tr and tr.tcs_id and not login:  # 11.1 manual route: a TCS ID entered by the master owner counts as a login
        login = Login(tcs_id=tr.tcs_id, login_date=None, product=None, source="manual")
    outcome = lead_outcome(st, status, rejected, login)
    closed = outcome in (R.LOGGED_IN, R.OUTCOME_REJECTED)

    # ---- 12.1 SO / branch action
    so_action = so_date = so_until = None
    cc_action = cc_date = None
    nxt = (answers or {}).get("next_date")
    nxt = date.fromisoformat(nxt) if isinstance(nxt, str) and nxt else None
    call_day = last.call_date if last else None
    if not closed:
        if status in (R.AMBER_WRONG_PERSON, R.DISCARDED_INVALID) or st.selection_status == R.NC_NO_NUMBER:
            so_action, so_date = R.ACT_CORRECT_NUMBER, call_day or st.entry_date
            so_until = st.entry_date + timedelta(days=cfg.correct_number_window_days)
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
                cc_action, cc_date = R.CC_FOLLOW_UP, ba.answer_date
                so_action = so_date = None
            else:
                so_date = ba.answer_date
        # ---- tracker (13.3): sent to the call centre by the master owner
        if tracker_wins and tr.owner == "call_centre" and tr.followup_date:
            cc_action, cc_date = R.CC_FOLLOW_UP, tr.followup_date
        if tracker_wins and tr.owner == "done":
            so_action = so_date = so_until = cc_action = cc_date = None
        # ---- 12.2 callback
        if status == R.IN_RETRY and callback:
            cc_action, cc_date = R.CC_CALLBACK, callback

    # 12.3: lead actions stay open until login or rejection; "correct number" for 15 days from the entry;
    # every other action for 14 days from its date. Expired actions are not "open".
    so_open = so_action is not None and (so_until is None or so_until >= today)
    cc_open = cc_action is not None and (cc_date is None or cc_date + timedelta(days=cfg.action_window_days) >= today)
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
    validated_on = None
    if validated:
        # 10: the date of the call that validated it, i.e. the first one; a login-only validation uses the login date
        validated_on = validating[0].call_date if R.is_validated(status) and validating else (login.login_date if login else None)
    return Derived(
        status=status, unanswered_count=unanswered, callback_date=callback, last_called_on=last_called, answers=answers,
        so_action=so_action if so_open else None, so_action_date=so_date if so_open else None,
        so_action_until=so_until if so_open else None,
        cc_action=cc_action if cc_open else None, cc_action_date=cc_date if cc_open else None,
        lead_outcome=outcome, rag=rag, rag_override=override, customer_validated=validated, validated_on=validated_on,
        green_channel=green_channel(answers, st.loan_requirement, cfg),
        expired_action=expired_action, expired_on=expired_on,
    )


# ---------------------------------------------------------------- 9 RAG
def rag_for(*, status: str | None, selection_status: str | None, unanswered: int, lead_outcome: str | None,
            has_open_action: bool, call_group: str | None = None, lost_lead: bool = False) -> str:
    """Section 9 (a manual override by the master owner is applied on top, by the caller).

    lost_lead: Red on a lead an earlier call had validated (the need has passed); section 9 makes a lost lead NA."""
    if lead_outcome in (R.LOGGED_IN, R.OUTCOME_REJECTED):
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
    The earliest entry wins (ties: lower Entry ID); it must be logged in and dated on or after Takeoff start."""
    if not candidates:
        return None
    entry_date, _, entry_id, logged_in = min(candidates, key=lambda c: (c[0], c[1]))
    return entry_id if logged_in and entry_date >= takeoff_start else None


def first_validated(candidates: list[tuple[str, str, bool]]) -> str | None:
    """candidates: (sort key, entry id, validated) of every entry with one phone number; the sort key orders entries
    by when they were made. Returns the id of the earliest validated entry: paid once per customer (section 10)."""
    vals = sorted((k, i) for k, i, v in candidates if v)
    return vals[0][1] if vals else None


# ---------------------------------------------------------------- 7 attempt limits
def attempt_allowed(*, call_group: str, attempts_today: int, days_called: set[date], today: date, cfg_tries_lead: int,
                    cfg_max_slots: int, cfg_tries_dsa: int, callback_days: set[date] = frozenset()) -> str | None:
    """Returns a reason when no further attempt may be recorded today, else None. call_group is the group whose
    calling rules apply (a converted DSA/CP is called as a lead)."""
    if call_group == "dsa_cp":
        # one calling day, plus a day the contact asked to be called back on (7.1 "Callback requested")
        if days_called and today not in days_called and today not in callback_days:
            return "A DSA/CP entry is called on one day only (or on the callback date it asked for)"
        if attempts_today >= cfg_tries_dsa:
            return f"A DSA/CP entry gets {cfg_tries_dsa} try a day"
        return None
    if attempts_today >= cfg_max_slots:
        return f"Up to {cfg_max_slots} attempts can be recorded per entry per day"
    return None
