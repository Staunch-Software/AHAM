"""The fixes from the feature review (docs/feature-review.md): one test per item, numbered as in the review."""
from datetime import date, timedelta

import pytest

from app.services.periods import today_local, tz_of
from app.services.sankalp import engine as E
from app.services.sankalp import rules as R
from tests.test_calling_flow import OK, Flow


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        day = date(2026, 10, 21)

    c = Clock()

    async def fake_today(s, company_id):
        return c.day

    for mod in ("app.services.sankalp.ops", "app.services.sankalp.handoff", "app.api.v1.calling", "app.api.v1.branch",
                "app.api.v1.reports", "app.api.v1.entries"):
        monkeypatch.setattr(f"{mod}.company_today", fake_today)
    return c


D = lambda d: date(2026, 10, d)  # noqa: E731


def att(day, outcome, row, answers=None, nxt=None, cycle=1):
    return E.Attempt(day, outcome, row, answers, nxt, cycle)


def state(*attempts, entry_date=D(10), group="lead"):
    return E.EntryState(entry_date=entry_date, call_group=group, selection_status=R.ALLOCATE, call_cycle=1,
                        attempts=list(attempts))


# ---------------------------------------------------------------- engine rules
def test_10_1_not_called_group_is_na_and_21_1_lost_lead_is_na():
    base = dict(selection_status=None, unanswered=0, lead_outcome=None, has_open_action=False)
    assert E.rag_for(status=None, call_group="none", **base) == "NA"
    assert E.rag_for(status=None, call_group="lead", **base) == "PENDING"
    assert E.rag_for(status=R.RED, lost_lead=True, **base) == "NA"
    assert E.rag_for(status=R.RED, **base) == "RED"
    assert E.rag_for(status=R.DSA_RED, lost_lead=True, **base) == "RED"


def test_13_1_a_dsa_cp_is_called_on_one_day_only_and_a_callback_request_closes_it():
    # as the Takeoff master: one try for a DSA/CP; asking for a callback closes it like an unanswered try
    kw = dict(call_group="dsa_cp", attempts_today=0, cfg_tries_lead=2, cfg_max_slots=3, cfg_tries_dsa=1)
    assert E.attempt_allowed(days_called={D(21)}, today=D(23), **kw)
    assert E.row_status(call_group="dsa_cp", outcome=R.CALLBACK, answers=None, unanswered_after=0,
                        max_unanswered=9) == R.CLOSED_NO_ANSWER
    assert E.row_status(call_group="lead", outcome=R.CALLBACK, answers=None, unanswered_after=0,
                        max_unanswered=9) == R.IN_RETRY


def test_22_1_validated_on_is_the_latest_call_that_gave_a_status_and_21_1_red_after_validation_is_na():
    ok = OK | {"next_step": "Call centre to continue"}
    st = state(att(D(12), R.CONNECTED, R.VALIDATED, ok), att(D(15), R.CONNECTED, R.VALIDATED, ok))
    assert E.derive(st, E.Settings(), D(16)).validated_on == D(15)  # as the Takeoff master
    st = state(att(D(12), R.CONNECTED, R.VALIDATED, ok), att(D(15), R.RNR, R.IN_RETRY))
    d = E.derive(st, E.Settings(), D(16))
    assert (d.status, d.validated_on, d.unanswered_count) == (R.VALIDATED, D(12), 1)  # an unanswered call gives none
    lost = state(att(D(12), R.CONNECTED, R.VALIDATED, ok),
                 att(D(15), R.CONNECTED, R.RED, {"loan_need": "Not looking for a loan"}))
    d = E.derive(lost, E.Settings(), D(16))
    assert (d.status, d.rag) == (R.RED, "NA")
    never = state(att(D(12), R.CONNECTED, R.RED, {"loan_need": "Not looking for a loan"}))
    assert E.derive(never, E.Settings(), D(16)).rag == "RED"


def test_24_1_an_action_whose_window_ran_out_is_kept_as_expired():
    st = state(att(D(12), R.WRONG_PERSON, R.AMBER_WRONG_PERSON))
    open_ = E.derive(st, E.Settings(), D(20))
    assert open_.so_action == R.ACT_CORRECT_NUMBER and open_.expired_action is None
    late = E.derive(st, E.Settings(), D(30))
    assert late.so_action is None and (late.expired_action, late.expired_on) == (R.ACT_CORRECT_NUMBER, D(25))


def test_15_1_converted_means_a_connected_yes_to_needs_home_loan():
    assert E.is_converted([att(D(12), R.CONNECTED, R.VALIDATED_CONVERTED, {"needs_home_loan": "Yes"})])
    assert not E.is_converted([att(D(12), R.CONNECTED, R.DSA_GREEN, {"needs_home_loan": "No", "dsa_rag": "Green"})])


# ---------------------------------------------------------------- through the API
async def test_10_1_existing_customer_stays_na_after_a_recalculation(client, tenant_a):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", category="existing_customer", phone="9000000101")
    assert (await f.get(e["id"]))["rag"] == "NA"
    r = await client.post(f"/api/v1/entries/{e['id']}/correct-so", headers=await f("monitor"),
                          json={"so_user_id": str(tenant_a["so2_id"])})
    assert r.status_code == 200, r.text
    assert (await f.get(e["id"]))["rag"] == "NA"


async def test_13_1_a_dsa_cp_callback_request_closes_it(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", category="dsa_connector", phone="9000000102")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    r = await f.call("caller1", e["id"], R.CALLBACK, next_date="2026-10-23")
    assert (r["status"], r["cc_action"]) == (R.CLOSED_NO_ANSWER, None)  # one try for a DSA/CP (Takeoff master)
    clock.day = D(23)
    await f.run(clock.day)
    assert e["entry_code"] not in await f.list("caller1")


async def test_15_1_converted_dsa_cp_follow_up_is_called_as_a_lead(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", category="dsa_connector", phone="9000000103")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    r = await f.call("caller1", e["id"], R.CONNECTED, {"needs_home_loan": "Yes", **OK,
                                                       "next_step": "Call centre to continue", "next_date": "2026-10-23"})
    assert (r["status"], r["cc_action"]) == (R.VALIDATED_CONVERTED, R.CC_TAKE_FORWARD)
    assert (await f.get(e["id"], "caller1"))["converted"] is True
    clock.day = D(23)
    await f.run(clock.day)
    assert (await f.list("caller1"))[e["entry_code"]]["kind"] == "followup"
    r = await f.call("caller1", e["id"], R.RNR)  # refused before the fix ("called on one day only")
    assert (r["status"], r["rag"]) == (R.VALIDATED_CONVERTED, "GREEN")  # an unanswered call keeps the status
    r = await f.call("caller1", e["id"], R.CONNECTED, OK | {"next_step": "Call centre to continue"}, slot="03-04")
    assert r["status"] == R.VALIDATED_CONVERTED  # the conversion holds without asking "needs a home loan?" again


async def test_3_2_rbh_corrects_numbers_only_where_a_branch_has_no_bm_and_no_rtm(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e2 = await f.entry("so2", phone="9000000104")  # Branch Two: no cluster, no BM
    e1 = await f.entry("so1", phone="9000000105")  # Branch One: has both
    await f.callers(clock.day, {"b1": "caller1", "b2": "caller1"})
    await f.run(clock.day)
    for e in (e1, e2):
        assert (await f.call("caller1", e["id"], R.WRONG_PERSON))["so_action"] == R.ACT_CORRECT_NUMBER
    r = await client.post(f"/api/v1/entries/{e2['id']}/correct-number", headers=await f("rm1"), json={"phone": "9123456780"})
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/entries/{e1['id']}/correct-number", headers=await f("rm1"), json={"phone": "9123456781"})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "bm_or_rtm_corrects"


async def _validated_visit(f, so, phone, clock, extra=None):
    e = await f.entry(so, phone=phone)
    await f.callers(clock.day, {"b1": "caller1", "b2": "caller1", "b3": "caller1"})
    await f.run(clock.day)
    r = await f.call("caller1", e["id"], R.CONNECTED,
                     OK | {"next_step": "SO / branch visit", "next_date": "2026-10-24"} | (extra or {}))
    assert r["so_action"] == R.ACT_VISIT, r
    return e


async def test_16_2_handling_branch_works_the_lead_and_16_3_card_changes_are_in_the_history(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await _validated_visit(f, "so1", "9000000106", clock)
    url = f"/api/v1/calls/entries/{e['id']}/lead-card"
    r = await client.put(url, headers=await f("caller1"),
                         json={"handling_branch_id": str(tenant_a["b3"]), "loan_requirement": 2_000_000})
    assert r.status_code == 200, r.text
    leads3 = (await client.get("/api/v1/branch/leads", headers=await f("bm3"))).json()["items"]
    assert [(i["entry_code"], i["handling_branch_name"]) for i in leads3] == [(e["entry_code"], "Branch Three")]
    assert (await client.get("/api/v1/branch/leads", headers=await f("bm1"))).json()["items"] == []
    url_a = f"/api/v1/branch/leads/{e['id']}/answer"
    assert (await client.post(url_a, headers=await f("bm1"), json={"code": "A1", "answer_date": "2026-10-25"})).status_code == 403
    assert (await client.post(url_a, headers=await f("bm3"), json={"code": "A1", "answer_date": "2026-10-25"})).status_code == 201
    d = await f.get(e["id"])
    assert d["so_name"] == "So1" and d["branch_name"] == "Branch One"  # credit stays with the SO's branch
    clock.day = date(2026, 10, 27)  # the promised login date has passed: a missed date of the handling branch only
    assert [m["missed"] for m in (await client.get("/api/v1/branch/missed-dates", headers=await f("bm3"))).json()] == [1]
    assert (await client.get("/api/v1/branch/missed-dates", headers=await f("bm1"))).json() == []
    await client.put(url, headers=await f("caller1"),
                     json={"handling_branch_id": str(tenant_a["b3"]), "loan_requirement": 2_500_000})
    cards = [h for h in (await f.get(e["id"]))["history"] if h["kind"] == "lead_card"]
    assert cards[-1]["detail"]["changes"] == {"loan_requirement": [2_000_000, 2_500_000]}
    assert cards[0]["detail"]["changes"]["handling_branch"] == [None, "Branch Three"]  # by name, not the id


async def test_25_1_and_25_2_tracker_outcomes_need_what_makes_them_work(client, tenant_a):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9000000107")
    url = f"/api/v1/calls/entries/{e['id']}/tracker"
    assert (await client.put(url, headers=await f("master"), json={"outcome": "Logged in"})).status_code == 422
    assert (await client.put(url, headers=await f("master"), json={"outcome": "Rejected"})).status_code == 422
    r = await client.put(url, headers=await f("master"), json={"outcome": R.TRACKER_RETURN_GREEN})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "no_green_channel_hold"
    r = await client.put(url, headers=await f("master"), json={"outcome": "Logged in", "tcs_id": "TCS-77"})
    assert r.status_code == 200 and r.json()["lead_outcome"] == R.LOGGED_IN


async def test_25_2_return_to_branch_on_the_tracker_returns_a_green_channel_rejection(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await _validated_visit(f, "so1", "9000000108", clock, {"loan_need": "Self-construction"})
    await client.put(f"/api/v1/calls/entries/{e['id']}/lead-card", headers=await f("caller1"),
                     json={"loan_requirement": 600_000})
    r = await client.post(f"/api/v1/branch/leads/{e['id']}/answer", headers=await f("bm1"), json={"code": "R2"})
    assert r.json()["green_channel"] == "pending"
    r = await client.put(f"/api/v1/calls/entries/{e['id']}/tracker", headers=await f("master"),
                         json={"outcome": R.TRACKER_RETURN_GREEN})
    assert r.status_code == 200, r.text
    d = await f.get(e["id"])
    assert d["branch_answers"][-1]["green_channel"] == "returned" and d["lead_outcome"] is None
    assert d["so_action"] == R.ACT_GREEN_LOGIN  # back with the branch to log in (Takeoff master)


async def test_12_1_a_callers_list_moves_to_another_caller(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    a = await f.entry("so1", phone="9000000109")
    b = await f.entry("so1", phone="9000000110", hhmm="11:00")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    r = await client.post("/api/v1/calls/allocations/move", headers=await f("master"),
                          json={"from_caller_id": str(tenant_a["caller1_id"]), "to_caller_id": str(tenant_a["caller2_id"])})
    assert r.json() == {"moved": 2}
    assert set(await f.list("caller2")) == {a["entry_code"], b["entry_code"]} and await f.list("caller1") == {}


async def test_12_2_first_try_overdue_and_12_3_priority_reason(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9000000111", day="2026-10-18")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    row = (await f.list("caller1"))[e["entry_code"]]
    assert row["first_try_overdue"] is True and row["priority_reason"] is None
    over = (await client.get("/api/v1/calls/allocations", headers=await f("master"))).json()
    assert over["first_try_overdue"] == 1
    await client.put(f"/api/v1/calls/entries/{e['id']}/tracker", headers=await f("master"), json={"immediate_callback": True})
    assert (await f.list("caller1"))[e["entry_code"]]["priority_reason"] == "Master owner: immediate call-back"


async def test_24_1_expired_actions_list_and_24_2_missed_dates(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    wrong = await f.entry("so1", phone="9000000112")
    near = await _validated_visit(f, "so1", "9000000113", clock)
    far = await _validated_visit(f, "so1", "9000000114", clock)
    await f.call("caller1", wrong["id"], R.WRONG_PERSON)
    ans = "/api/v1/branch/leads/{}/answer"
    await client.post(ans.format(near["id"]), headers=await f("bm1"), json={"code": "A1", "answer_date": "2026-10-25"})
    r = await client.post(ans.format(far["id"]), headers=await f("bm1"), json={"code": "D", "answer_date": "2026-11-20"})
    assert r.json()["cc_action"] == R.CC_FOLLOW_UP  # beyond 14 days: the call centre's date
    clock.day = date(2026, 11, 25)
    await f.run(clock.day)
    missed = (await client.get("/api/v1/branch/missed-dates", headers=await f("bm1"))).json()
    assert missed == [{"branch_id": str(tenant_a["b1"]), "branch": "Branch One", "missed": 1}]
    expired = (await client.get("/api/v1/branch/actions?expired=true", headers=await f("bm1"))).json()
    rows = {i["entry_code"]: i for i in expired["items"]}
    assert rows[wrong["entry_code"]]["expired_action"] == R.ACT_CORRECT_NUMBER
    assert rows[wrong["entry_code"]]["expired_on"] == "2026-11-04"
    open_ = (await client.get("/api/v1/branch/actions", headers=await f("bm1"))).json()
    assert {"items", "total", "page", "page_size"} <= set(open_) and wrong["entry_code"] not in {
        i["entry_code"] for i in open_["items"]}


async def test_4_1_a_holiday_added_late_moves_that_days_entries(client, tenant_a):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9000000115", day="2026-10-22")
    assert (await f.get(e["id"]))["count_date"] == "2026-10-22"
    r = await client.post("/api/v1/holidays", headers=await f("monitor"), json={"day": "2026-10-22", "name": "Local"})
    assert r.status_code == 201 and r.json()["entries_moved"] == 1
    assert (await f.get(e["id"]))["count_date"] == "2026-10-23"
    assert (await client.delete(f"/api/v1/holidays/{r.json()['id']}", headers=await f("monitor"))).status_code == 204
    assert (await f.get(e["id"]))["count_date"] == "2026-10-22"


async def test_5_1_an_entry_made_after_the_clock_was_set_back_is_flagged(client, tenant_a):
    f = Flow(client, tenant_a)
    ok = await f.entry("so1", phone="9000000116", hhmm="10:00", device_clock_at_last_contact="2026-10-20T09:30:00+05:30")
    back = await f.entry("so1", phone="9000000117", hhmm="10:00", device_clock_at_last_contact="2026-10-20T18:00:00+05:30")
    assert (await f.get(ok["id"]))["device_time_suspect"] is False
    assert (await f.get(back["id"]))["device_time_suspect"] is True


async def test_26_2_past_days_keep_their_targets_and_1_2_the_audit_keeps_old_and_new(client, tenant_a):
    f = Flow(client, tenant_a)
    r = await client.patch("/api/v1/settings", headers=await f("admin"), json={"daily_entry_target": 12})
    assert r.status_code == 200 and r.json()["daily_entry_target"] == 12
    today = today_local(tz_of("Asia/Kolkata"))
    past = (await client.get("/api/v1/compliance?day=2026-10-20", headers=await f("monitor"))).json()
    now = (await client.get(f"/api/v1/compliance?day={today}", headers=await f("monitor"))).json()
    assert (past["entry_target"], now["entry_target"]) == (10, 12)
    log = (await client.get("/api/v1/audit-logs", headers=await f("admin"))).json()["items"][0]
    assert log["action"] == "settings.update"
    assert log["details"] == {"daily_entry_target": {"old": 10, "new": 12}}


async def test_9_2_compliance_filters_totals_and_export(client, tenant_a):
    f = Flow(client, tenant_a)
    await f.entry("so1", phone="9000000118")
    data = (await client.get(f"/api/v1/compliance?day=2026-10-20&region_id={tenant_a['r1']}&q=so1",
                             headers=await f("monitor"))).json()
    assert [i["emp_code"] for i in data["items"]] == [tenant_a["so1_code"]]
    assert data["items"][0]["region"] == "Region One" and "met_lead_target" in data["items"][0]
    assert {"met_target", "met_lead_target", "expected"} <= set(data["summary"])
    csv = (await client.get("/api/v1/compliance/export.csv?date_from=2026-10-20&date_to=2026-10-20",
                            headers=await f("monitor"))).text
    head = csv.splitlines()[0]
    for col in ("Region", "Lead/Prospect shortfall", "Met entry target", "Met Lead/Prospect target"):
        assert col in head


async def test_3_3_who_heads_what_and_28_1_branch_names_are_unique(client, tenant_a):
    f = Flow(client, tenant_a)
    m = (await client.get("/api/v1/org/managers", headers=await f("admin"))).json()
    assert m["branches"][str(tenant_a["b1"])] == ["Bm1"] and str(tenant_a["b2"]) not in m["branches"]
    assert m["regions"][str(tenant_a["r1"])] == ["Rm1"] and m["clusters"][str(tenant_a["c1"])] == ["Cm1"]
    r = await client.post("/api/v1/branches", headers=await f("admin"),
                          json={"name": "Branch One", "code": "BX1", "region_id": str(tenant_a["r1"])})
    assert r.status_code == 409


async def test_1_1_limits_for_screen_texts_27_1_map_says_when_it_is_cut_8_1_holidays_for_the_app(client, tenant_a):
    f = Flow(client, tenant_a)
    meta = (await client.get("/api/v1/sankalp/meta", headers=await f("caller1"))).json()
    assert meta["limits"]["max_unanswered_lead"] == 9 and meta["limits"]["green_channel_purchase_limit"] == 1_500_000
    mp = (await client.get("/api/v1/map/entries", headers=await f("monitor"))).json()
    assert mp["capped"] is False and mp["limit"] == 3000 and mp["shown"] == mp["total"]
    await client.post("/api/v1/holidays", headers=await f("monitor"),
                      json={"day": str(today_local(tz_of("Asia/Kolkata")) + timedelta(days=3)), "name": "Fest"})
    summ = (await client.get("/api/v1/me/summary", headers=await f("so1"))).json()
    assert summ["correct_number_window_days"] == 15 and len(summ["holidays"]) == 1


async def test_copy_yesterday_on_a_monday_copies_saturday(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    await f.callers(D(24), {"b1": "caller1"})  # Saturday; nobody is set for the Sunday
    r = await client.post("/api/v1/calls/caller-days/copy", headers=await f("master"),
                          json={"from_day": str(D(25)), "to_day": str(D(26))})
    assert r.status_code == 200, r.text
    got = {i["branch_id"]: i["caller_id"] for i in r.json()["items"]}
    assert got[str(tenant_a["b1"])] == str(tenant_a["caller1_id"])


def test_last_week_period_is_monday_to_sunday_before_this_week():
    from datetime import datetime, timezone

    from app.services.periods import period_bounds
    now = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)  # Monday 2 Nov, 11:30 in India
    assert period_bounds("last_week", tz_of("Asia/Kolkata"), now=now)[2:] == (date(2026, 10, 26), date(2026, 11, 1))


async def test_existing_customer_counts_as_not_called_on_the_dashboard(client, tenant_a):
    f = Flow(client, tenant_a)
    await f.entry("so1", phone="9000000120", category="existing_customer")
    await f.entry("so1", phone="9000000121", hhmm="11:00")
    r = await client.get("/api/v1/dashboard", headers=await f("monitor"),
                         params={"period": "custom", "date_from": "2026-10-20", "date_to": "2026-10-20"})
    assert r.json()["by_status"] == {"Not called (existing customer / applicant)": 1, "Pending": 1}


async def test_changing_a_branchs_caller_after_the_run_moves_its_uncalled_new_entries(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    a = await f.entry("so1", phone="9000000131")
    b = await f.entry("so1", phone="9000000132", hhmm="11:00")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", a["id"], R.RNR)  # caller1 has called `a`: it is theirs now
    url, body = "/api/v1/calls/caller-days", lambda c: {"day": str(clock.day), "assignments": [
        {"branch_id": str(tenant_a["b1"]), "caller_id": str(tenant_a[f"{c}_id"])}]}
    r = await client.put(url, headers=await f("master"), json=body("caller2"))
    assert r.json()["moved"] == 1
    assert set(await f.list("caller2")) == {b["entry_code"]} and set(await f.list("caller1")) == {a["entry_code"]}
    # saving again without a change moves nothing back, even after a list was moved for an absent caller
    await client.post("/api/v1/calls/allocations/move", headers=await f("master"),
                      json={"from_caller_id": str(tenant_a["caller2_id"]), "to_caller_id": str(tenant_a["caller1_id"])})
    r = await client.put(url, headers=await f("master"), json=body("caller2"))
    assert r.json()["moved"] == 0 and await f.list("caller2") == {}
