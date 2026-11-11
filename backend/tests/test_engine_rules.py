"""The rule tables of the business logic, checked one row at a time (pure functions, no database)."""
from datetime import date, timedelta

import pytest

from app.services.sankalp import engine as E
from app.services.sankalp import rules as R

D = date(2026, 10, 20)
CFG = E.Settings()


# ---------------------------------------------------------------- 5.2 fresh
@pytest.mark.parametrize("over,fresh", [
    ({}, True),
    ({"selected": True}, False),  # already evaluated
    ({"call_group": "none"}, False),  # existing customer / applicant
    ({"entry_date": date(2026, 9, 23)}, False),  # before the first call date
    ({"entry_date": D + timedelta(days=1)}, False),  # same day as the run: next day only
    ({"entry_date": D + timedelta(days=1), "same_day_calling": True}, True),
])
def test_is_fresh(over, fresh):
    args = dict(has_code=True, selected=False, call_group="lead", entry_date=D, first_call_date=date(2026, 9, 24),
                run_date=D + timedelta(days=1), same_day_calling=False) | over
    assert E.is_fresh(**args) is fresh


# ---------------------------------------------------------------- 5.3 order of checks
BASE = dict(call_group="lead", phone_valid=True, repeat_by_same_so=False, earlier_fresh_same_number=False,
            number_in_retry=False, spoken_within_window=False, ever_spoken=False)


@pytest.mark.parametrize("over,result", [
    ({}, R.ALLOCATE),
    ({"phone_valid": False, "repeat_by_same_so": True}, R.NC_NO_NUMBER),  # 1 before everything
    ({"repeat_by_same_so": True, "earlier_fresh_same_number": True}, R.NC_REPEAT),  # 2 before 3
    ({"call_group": "dsa_cp", "repeat_by_same_so": True}, R.ALLOCATE),  # 2 is for the Lead group only
    ({"earlier_fresh_same_number": True, "number_in_retry": True}, R.NC_DUPLICATE),  # 3 before 4
    ({"number_in_retry": True, "spoken_within_window": True}, R.NC_BEING_CALLED),  # 4 before 5
    ({"spoken_within_window": True, "ever_spoken": True}, R.NC_SPOKEN),
    ({"call_group": "dsa_cp", "spoken_within_window": True, "ever_spoken": True}, R.NC_KNOWN),  # 5 Lead only, 6 DSA/CP
    ({"ever_spoken": True}, R.ALLOCATE),  # a lead spoken to more than 30 days ago is called again
    ({"call_group": "dsa_cp", "ever_spoken": True}, R.NC_KNOWN),
])
def test_selection_order(over, result):
    assert E.selection_decision(**(BASE | over)) == result


# ---------------------------------------------------------------- 8.1 lead logic, in order
OK = {"loan_need": "Home purchase", "documents": "Yes", "relationship": "No", "name_check": "Same person", "visit": "Yes"}


@pytest.mark.parametrize("over,status", [
    ({"loan_need": None}, R.AMBER_MISSING),
    ({"loan_need": "Not looking for a loan"}, R.RED),
    ({"loan_need": "LAP", "documents": "File already logged with Aham"}, R.NOT_COUNTED_LAP),  # 3 before 4
    ({"loan_need": "BT + LAP"}, R.NOT_COUNTED_LAP),
    ({"documents": "File already logged with Aham", "relationship": "Yes – the same officer"}, R.ALREADY_IN_PROCESS),
    ({"relationship": "Yes – the same officer", "name_check": "Different person"}, R.AMBER_KNOWS_SO),
    ({"relationship": "Yes – another employee"}, R.VALIDATED),
    ({"name_check": "Different person – same family", "visit": "No"}, R.VALIDATED_DIFFERENT),  # 6 before 7
    ({"visit": "No"}, R.VALIDATED_NO_VISIT),
    ({"visit": "Don't recall"}, R.VALIDATED),
    ({}, R.VALIDATED),
])
def test_lead_logic(over, status):
    assert E.lead_logic({k: v for k, v in (OK | over).items() if v is not None}) == status


@pytest.mark.parametrize("answers,status", [
    ({"dsa_rag": "Green"}, R.DSA_GREEN), ({"dsa_rag": "NA"}, R.DSA_NA), ({"dsa_rag": "Amber"}, R.DSA_AMBER),
    ({"dsa_rag": "Red"}, R.DSA_RED), ({}, R.DSA_NO_RAG), ({"needs_home_loan": "No", "dsa_rag": "Red"}, R.DSA_RED),
    ({"needs_home_loan": "Yes", **OK}, R.VALIDATED_CONVERTED),
    ({"needs_home_loan": "Yes", **OK, "visit": "No"}, R.VALIDATED_CONVERTED),  # any Validated… becomes converted
    ({"needs_home_loan": "Yes", "loan_need": "Not looking for a loan"}, R.RED),
])
def test_dsa_logic(answers, status):
    assert E.dsa_logic(answers) == status


# ---------------------------------------------------------------- 8.3 not connected
@pytest.mark.parametrize("group,outcome,after,status", [
    ("lead", R.INVALID_NUMBER, 0, R.DISCARDED_INVALID),
    ("lead", R.WRONG_PERSON, 0, R.AMBER_WRONG_PERSON),
    ("lead", R.REFUSED, 0, R.REJECTED_REFUSED),
    ("lead", R.CALLBACK, 0, R.IN_RETRY),
    ("dsa_cp", R.BUSY, 1, R.CLOSED_NO_ANSWER),
    ("lead", R.RNR, 1, R.IN_RETRY),
    ("lead", R.SWITCHED_OFF, 8, R.IN_RETRY),
    ("lead", R.NOT_REACHABLE, 9, R.DISCARDED_9),
])
def test_not_connected(group, outcome, after, status):
    assert E.row_status(call_group=group, outcome=outcome, answers=None, unanswered_after=after, max_unanswered=9) == status


# ---------------------------------------------------------------- 9 RAG
@pytest.mark.parametrize("kw,rag", [
    ({}, "PENDING"),
    ({"selection_status": R.ALLOCATE}, "PENDING"),  # waiting to be called
    ({"selection_status": R.NC_NO_NUMBER}, "AMBER"),
    ({"selection_status": R.NC_REPEAT}, "NA"),
    ({"selection_status": R.NC_KNOWN}, "NA"),
    ({"status": R.RED}, "RED"), ({"status": R.DSA_RED}, "RED"),
    ({"status": R.AMBER_KNOWS_SO}, "AMBER"), ({"status": R.DSA_AMBER}, "AMBER"), ({"status": R.DISCARDED_INVALID}, "AMBER"),
    ({"status": R.IN_RETRY, "unanswered": 2}, "RNR"), ({"status": R.IN_RETRY}, "GREEN"),
    ({"status": R.DISCARDED_9}, "RNR"), ({"status": R.CLOSED_NO_ANSWER}, "RNR"),
    ({"status": R.DSA_GREEN}, "GREEN"), ({"status": R.DSA_NA}, "NA"),
    ({"status": R.VALIDATED, "has_open_action": True}, "GREEN"),
    ({"status": R.VALIDATED}, "NA"),
    ({"status": R.REJECTED_REFUSED}, "NA"),
    ({"status": R.RED, "lead_outcome": R.LOGGED_IN}, "NA"),  # logged in or rejected
    ({"status": R.VALIDATED, "has_open_action": True, "lead_outcome": R.OUTCOME_REJECTED}, "NA"),
])
def test_rag(kw, rag):
    args = dict(status=None, selection_status=None, unanswered=0, lead_outcome=None, has_open_action=False) | kw
    assert E.rag_for(**args) == rag


# ---------------------------------------------------------------- derive: actions (12), outcome (11), flags (10)
def att(outcome=R.CONNECTED, answers=None, day=D, cycle=1, nxt=None, group="lead"):
    st = E.row_status(call_group=group, outcome=outcome, answers=answers, unanswered_after=1, max_unanswered=9)
    return E.Attempt(day, outcome, st, answers if outcome == R.CONNECTED else None, nxt, cycle)


def state(*attempts, **kw):
    return E.EntryState(entry_date=D - timedelta(days=1), call_group=kw.pop("group", "lead"),
                        selection_status=kw.pop("sel", R.ALLOCATE), call_cycle=kw.pop("cycle", 1),
                        attempts=list(attempts), **kw)


def test_actions_after_a_validated_call():
    visit = E.derive(state(att(answers=OK | {"next_step": "SO / branch visit", "next_date": "2026-10-24"})), CFG, D)
    assert (visit.so_action, visit.so_action_date, visit.so_action_until) == (R.ACT_VISIT, date(2026, 10, 24), None)
    assert visit.rag == "GREEN" and visit.customer_validated and visit.validated_on == D
    cc = E.derive(state(att(answers=OK | {"next_step": "Call centre to continue", "next_date": "2026-10-22"})), CFG, D)
    assert cc.so_action is None and (cc.cc_action, cc.cc_action_date) == (R.CC_TAKE_FORWARD, date(2026, 10, 22))
    docs = E.derive(state(att(answers=OK | {"documents": "Partly"})), CFG, D)
    assert docs.so_action == R.ACT_COLLECT_DOCS
    plain = E.derive(state(att(answers=OK)), CFG, D)
    assert plain.so_action == R.ACT_FOLLOW_UP_LEAD
    lap = E.derive(state(att(answers=OK | {"loan_need": "LAP"})), CFG, D)
    assert lap.so_action == R.ACT_FOLLOW_UP_LEAD and not lap.customer_validated  # LAP: action, not counted
    # lead actions never expire
    late = E.derive(state(att(answers=OK)), CFG, D + timedelta(days=200))
    assert late.so_action == R.ACT_FOLLOW_UP_LEAD and late.rag == "GREEN"


def test_correct_number_action_has_a_15_day_window():
    st = state(att(R.WRONG_PERSON))
    d = E.derive(st, CFG, D)
    assert d.status == R.AMBER_WRONG_PERSON and d.so_action == R.ACT_CORRECT_NUMBER and d.rag == "AMBER"
    call = st.attempts[-1].call_date
    assert d.so_action_until == call + timedelta(days=15)  # from the call that found it (Takeoff master)
    expired = E.derive(st, CFG, call + timedelta(days=16))
    assert expired.so_action is None and expired.rag == "AMBER"  # status still Amber
    nc = E.derive(state(sel=R.NC_NO_NUMBER), CFG, D)
    assert nc.so_action == R.ACT_CORRECT_NUMBER and nc.rag == "AMBER"


def test_dsa_follow_up_expires_after_14_days():
    d = E.derive(state(att(answers={"dsa_rag": "Green"}, group="dsa_cp"), group="dsa_cp"), CFG, D)
    assert d.so_action == R.ACT_DSA_FOLLOWUP and d.so_action_until == D + timedelta(days=14) and d.rag == "GREEN"
    assert E.derive(state(att(answers={"dsa_rag": "Green"}, group="dsa_cp"), group="dsa_cp"), CFG,
                    D + timedelta(days=15)).so_action is None


def test_callback_is_a_call_centre_action():
    d = E.derive(state(att(R.CALLBACK, nxt=D + timedelta(days=2))), CFG, D)
    assert d.status == R.IN_RETRY and d.callback_date == D + timedelta(days=2)
    assert (d.cc_action, d.cc_action_date) == (R.CC_CALLBACK, D + timedelta(days=2)) and d.rag == "GREEN"


def test_new_cycle_after_number_correction_is_in_retry_with_no_tries():
    d = E.derive(state(att(R.WRONG_PERSON), cycle=2), CFG, D)
    assert d.status == R.IN_RETRY and d.unanswered_count == 0 and d.rag == "GREEN" and d.so_action is None


def test_branch_answer_14_day_rule():
    base = att(answers=OK)
    near = E.derive(state(base, branch_answer=E.BranchAns("A1", D + timedelta(days=14), D)), CFG, D)
    assert near.so_action == R.ACT_FOLLOW_UP_LEAD and near.so_action_date == D + timedelta(days=14)
    far = E.derive(state(base, branch_answer=E.BranchAns("D", D + timedelta(days=15), D)), CFG, D)
    assert far.so_action is None and (far.cc_action, far.cc_action_date) == (R.CC_FOLLOW_UP, D + timedelta(days=15))


def test_rejections_and_green_channel():
    base = att(answers=OK)
    r4 = E.derive(state(base, branch_answer=E.BranchAns("R4", None, D)), CFG, D)
    assert r4.lead_outcome == R.OUTCOME_REJECTED and r4.so_action is None and r4.rag == "NA"
    held = E.derive(state(base, branch_answer=E.BranchAns("R2", None, D, "pending")), CFG, D)
    assert held.lead_outcome is None and held.so_action == R.ACT_FOLLOW_UP_LEAD
    returned = E.derive(state(base, branch_answer=E.BranchAns("R3", None, D, "returned")), CFG, D)
    assert returned.lead_outcome is None
    accepted = E.derive(state(base, branch_answer=E.BranchAns("R3", None, D, "accepted")), CFG, D)
    assert accepted.lead_outcome == R.OUTCOME_REJECTED


@pytest.mark.parametrize("need,amount,green", [
    ("Self-construction", 800_000, True), ("Self-construction", 800_001, False),
    ("Improvement or extension", 500_000, True), ("Home purchase", 1_500_000, True), ("Plot + construction", 1_600_000, False),
    ("Balance transfer", 100_000, False), ("BT + construction", 100_000, False), ("Home purchase", None, False),
])
def test_green_channel_limits(need, amount, green):
    assert E.green_channel({"loan_need": need}, amount, CFG) is green


def test_tracker_and_branch_answer_later_date_wins():
    base = att(answers=OK)
    newer_tracker = E.Tracker("call_centre", D + timedelta(days=3), None, None, None, False, D)
    d = E.derive(state(base, branch_answer=E.BranchAns("A1", D + timedelta(days=2), D), tracker=newer_tracker), CFG, D)
    assert (d.cc_action, d.cc_action_date) == (R.CC_FOLLOW_UP, D + timedelta(days=3))
    old_tracker = E.Tracker(None, None, "Rejected", None, None, False, D - timedelta(days=5))
    d = E.derive(state(base, branch_answer=E.BranchAns("A1", D + timedelta(days=2), D), tracker=old_tracker), CFG, D)
    assert d.lead_outcome is None  # the branch answer is newer than the tracker's rejection
    d = E.derive(state(base, tracker=E.Tracker(None, None, None, None, "RED", False, D)), CFG, D)
    assert d.rag == "GREEN" and d.rag_override == "RED"  # the override is applied on top


def test_login_outcomes_and_validation():
    base = att(answers=OK | {"loan_need": "Not looking for a loan"})  # Red
    after = E.derive(state(base, login=E.Login("T1", D + timedelta(days=5), "Home Loan", "register")), CFG, D)
    assert after.lead_outcome == R.LOGGED_IN and after.customer_validated and after.rag == "NA"
    assert after.validated_on == D  # the latest call that gave a status (Takeoff master), not the login date
    before = E.derive(state(base, login=E.Login("T1", D - timedelta(days=1), "Home Loan", "register")), CFG, D)
    assert before.lead_outcome == R.LOGIN_BEFORE_ENTRY and not before.customer_validated and before.rag == "NA"
    lap = E.derive(state(base, login=E.Login("T1", D + timedelta(days=5), "LAP", "register")), CFG, D)
    assert lap.lead_outcome == R.LOGGED_IN and not lap.customer_validated  # LAP login: success, not validation
    manual = E.derive(state(base, tracker=E.Tracker(None, None, None, "T9", None, False, D)), CFG, D)
    assert manual.lead_outcome == R.LOGGED_IN
    repeat = E.derive(state(sel=R.NC_REPEAT, login=E.Login("T1", D + timedelta(days=5), "Home Loan", "register")), CFG, D)
    assert not repeat.customer_validated  # never paid for a repeat entry
    dsa = E.derive(state(att(answers={"dsa_rag": "Green"}, group="dsa_cp"), group="dsa_cp",
                         login=E.Login("T1", D + timedelta(days=5), None, "register")), CFG, D)
    assert dsa.lead_outcome is None  # lead outcome applies to lead-type entries only


def test_success_and_first_validation():
    t = date(2026, 9, 22)
    assert E.sankalp_success_winner([(D, "B-1", "b", True), (D, "A-1", "a", True)], t) == "a"  # tie: lower Entry ID
    # only logged-in entries compete (Takeoff master): an earlier entry that did not log in does not block a later one
    assert E.sankalp_success_winner([(D, "A-1", "a", False), (D + timedelta(days=1), "B-1", "b", True)], t) == "b"
    assert E.sankalp_success_winner([(D, "A-1", "a", False)], t) is None
    assert E.sankalp_success_winner([(date(2026, 9, 1), "A", "a", True)], t) is None  # before Takeoff start
    assert E.first_validated([("2", "b", True), ("1", "a", False), ("3", "c", True)]) == "b"
    assert E.first_validated([("1", "a", False)]) is None


def test_attempt_limits():
    kw = dict(cfg_tries_lead=2, cfg_max_slots=3, cfg_tries_dsa=1, today=D)
    assert E.attempt_allowed(call_group="lead", attempts_today=2, days_called={D}, **kw) is None  # 3 slots a day
    assert E.attempt_allowed(call_group="lead", attempts_today=3, days_called={D}, **kw)
    assert E.attempt_allowed(call_group="dsa_cp", attempts_today=0, days_called=set(), **kw) is None
    assert E.attempt_allowed(call_group="dsa_cp", attempts_today=1, days_called={D}, **kw)
    assert E.attempt_allowed(call_group="dsa_cp", attempts_today=0, days_called={D - timedelta(days=1)}, **kw)


# ---------------------------------------------------------------- second alignment with the Takeoff master
UNANSWERED = R.RNR


def test_tracker_versus_branch_answer_ties_go_to_the_branch():
    base = att(answers=OK)
    same_day = E.Tracker("call_centre", D, None, None, None, False, D)
    d = E.derive(state(base, branch_answer=E.BranchAns("A1", D + timedelta(days=2), D), tracker=same_day), CFG, D)
    assert d.cc_action is None and d.so_action_date == D + timedelta(days=2)  # the branch's answer applies
    # a tracker row with no follow-up date never overrides a branch answer, however recently it was saved
    undated = E.Tracker(None, None, "Rejected", None, None, False, D + timedelta(days=1))
    d = E.derive(state(base, branch_answer=E.BranchAns("A1", D + timedelta(days=2), D), tracker=undated), CFG, D)
    assert d.lead_outcome is None


def test_reopen_runs_from_its_date_until_a_call_gives_a_status():
    called = att(answers=OK, day=D - timedelta(days=3))
    later = D + timedelta(days=2)
    reopen = E.Tracker("call_centre", later, R.TRACKER_REOPEN, None, None, False, D)
    d = E.derive(state(called, tracker=reopen), CFG, D)
    assert d.status == R.IN_RETRY and d.callback_date == later and not d.priority  # a normal retry from its date
    d = E.derive(state(called, att(UNANSWERED, day=later), tracker=reopen), CFG, later)
    assert d.status == R.IN_RETRY  # an unanswered try gives no status: still reopened
    d = E.derive(state(called, att(answers=OK, day=later), tracker=reopen), CFG, later)
    assert d.status == R.VALIDATED  # reached on the reopen date
    # with the master owner's immediate call-back the reopen is PRIORITY, from the day it was saved
    hot = E.Tracker("call_centre", None, R.TRACKER_REOPEN, None, None, True, D)
    d = E.derive(state(called, tracker=hot), CFG, D)
    assert d.priority and d.priority_reason == "Master owner: immediate call-back" and d.callback_date == D
    # an immediate call-back on its own only puts a not-yet-called entry first
    alone = E.Tracker("call_centre", None, None, None, None, True, D)
    assert E.derive(state(tracker=alone), CFG, D).priority
    assert not E.derive(state(called, tracker=alone), CFG, D).priority
    # branch code 3: PRIORITY, with the branch's answer date as the callback
    d = E.derive(state(called, branch_answer=E.BranchAns("3", None, D)), CFG, D)
    assert d.priority and d.status == R.IN_RETRY and d.callback_date == D


def test_login_rules_close_the_entry():
    base = att(answers=OK, day=D - timedelta(days=1))
    # a register row without a login date counts as a login on or before the entry date: closed, even for code 3
    nodate = E.derive(state(base, login=E.Login("T1", None, "Home Loan", "register"),
                            branch_answer=E.BranchAns("3", None, D)), CFG, D)
    assert nodate.lead_outcome == R.LOGIN_BEFORE_ENTRY and nodate.rag == "NA"
    assert nodate.so_action is None and nodate.cc_action is None and not nodate.priority
    # a TCS ID typed on the tracker overrides the register
    over = E.derive(state(base, login=E.Login("T1", D - timedelta(days=3), "Home Loan", "register"),
                          tracker=E.Tracker(None, None, None, "T9", None, False, D)), CFG, D)
    assert over.lead_outcome == R.LOGGED_IN


def test_callback_is_the_latest_next_date_on_calls_that_did_not_connect():
    nxt = D + timedelta(days=3)
    d = E.derive(state(att(R.CALLBACK, nxt=D + timedelta(days=1)), att(UNANSWERED, nxt=nxt)), CFG, D)
    assert d.status == R.IN_RETRY and d.callback_date == nxt and (d.cc_action, d.cc_action_date) == (R.CC_CALLBACK, nxt)
    # no callback action while the tracker gives the entry to the branch
    to_branch = E.Tracker("branch", D + timedelta(days=5), None, None, None, False, D)
    d = E.derive(state(att(UNANSWERED, nxt=nxt), tracker=to_branch), CFG, D)
    assert d.cc_action is None and d.so_action == R.ACT_BRANCH_FOLLOWUP


def test_a_lead_action_on_the_tracker_makes_a_lead_whatever_its_owner():
    dsa = att(answers={"dsa_rag": "Green"}, group="dsa_cp")
    tr = E.Tracker("call_centre", D + timedelta(days=1), None, None, None, False, D, R.ACT_VISIT)
    d = E.derive(state(dsa, group="dsa_cp", tracker=tr, login=E.Login("T1", D + timedelta(days=5), None, "register")),
                 CFG, D)
    assert d.lead_outcome == R.LOGGED_IN
