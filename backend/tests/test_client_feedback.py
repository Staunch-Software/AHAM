"""Fixes from the second review against the business-logic document (Nov 2026) and the client's demo feedback."""
from datetime import date

import pytest

from app.services.periods import today_local, tz_of
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


VISIT = OK | {"next_step": "SO / branch visit", "next_date": "2026-10-24"}


async def test_a_dsa_cp_entry_with_a_corrected_number_is_called_again(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", category="dsa_connector", phone="9300000001")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    r = await f.call("caller1", e["id"], R.INVALID_NUMBER)
    assert r["so_action"] == R.ACT_CORRECT_NUMBER
    fix = await client.post(f"/api/v1/entries/{e['id']}/correct-number", headers=await f("bm1"), json={"phone": "9300000002"})
    assert fix.status_code == 200, fix.text
    clock.day = date(2026, 10, 22)
    await f.callers(clock.day, {"b1": "caller1"})
    assert (await f.run(clock.day))["allocated"] == {"retry": 1}
    # the one DSA/CP calling day counts from the correction, not from the call to the wrong number (13.2)
    r = await f.call("caller1", e["id"], R.CONNECTED, {"dsa_rag": "Green", "needs_home_loan": "No"})
    assert r["status"] == R.DSA_GREEN


async def test_a_lead_can_take_a_third_try_the_same_day(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000011")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.RNR, slot="10-11")
    await f.call("caller1", e["id"], R.BUSY, slot="03-04")
    lst = (await client.get("/api/v1/calls/my-list", headers=await f("caller1"))).json()
    assert lst["items"] == [] and [i["entry_code"] for i in lst["called_today"]] == [e["entry_code"]]
    r = await f.call("caller1", e["id"], R.RNR, slot="05-06")  # 7.1: two planned, up to three recorded
    assert r["unanswered_count"] == 3
    lst = (await client.get("/api/v1/calls/my-list", headers=await f("caller1"))).json()
    assert lst["called_today"] == []
    r = await f.call("caller1", e["id"], R.RNR, slot="06-07", expect=409)
    assert r["detail"]["code"] == "attempt_limit"
    await f.call("caller2", e["id"], R.RNR, expect=404)  # someone else's entry stays out of reach


async def test_a_follow_up_is_done_once_called_and_stays_open_until_then(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    called, missed = await f.entry("so1", phone="9300000021"), await f.entry("so1", hhmm="11:00", phone="9300000022")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    for e in (called, missed):
        await f.call("caller1", e["id"], R.CONNECTED, VISIT)
        r = await client.post(f"/api/v1/branch/leads/{e['id']}/answer", headers=await f("bm1"),
                              json={"code": "D", "answer_date": "2026-11-20"})
        assert r.json()["cc_action"] == R.CC_FOLLOW_UP and r.json()["so_action"] is None
    clock.day = date(2026, 11, 20)
    await f.callers(clock.day, {"b1": "caller1"})
    assert (await f.run(clock.day))["allocated"] == {"followup": 2}
    r = await f.call("caller1", called["id"], R.CONNECTED, VISIT | {"next_date": "2026-11-23"})
    assert (r["cc_action"], r["so_action"]) == (None, R.ACT_VISIT)  # back with the branch
    clock.day = date(2026, 11, 21)
    await f.callers(clock.day, {"b1": "caller1"})
    assert called["entry_code"] not in await f.list("caller1")
    # the other follow-up was never called: as the Takeoff master, it does not expire; it stays on the list
    clock.day = date(2026, 12, 5)
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    d = await f.get(missed["id"])
    assert (d["cc_action"], d["so_action"], d["rag"], d["expired_action"]) == (R.CC_FOLLOW_UP, None, "GREEN", None)
    assert (await f.list("caller1"))[d["entry_code"]]["kind"] == "followup"


async def test_branch_code_3_puts_the_lead_on_todays_list_at_once(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000031")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.CONNECTED, VISIT)
    assert e["entry_code"] not in await f.list("caller1")
    r = await client.post(f"/api/v1/branch/leads/{e['id']}/answer", headers=await f("bm1"), json={"code": "3"})
    assert r.status_code == 201, r.text
    item = (await f.list("caller1"))[e["entry_code"]]  # no new run needed (6.2)
    assert item["kind"] == "priority" and item["priority_reason"]
    await f.call("caller1", e["id"], R.CONNECTED, VISIT)  # PRIORITY may be called again the same day


async def test_an_earlier_entry_that_was_never_selected_still_makes_a_repeat(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    await f.entry("so1", day="2026-10-15", category="existing_customer", phone="9300000041")
    e = await f.entry("so1", phone="9300000041")
    await f.callers(clock.day, {"b1": "caller1"})
    assert (await f.run(clock.day))["selection"] == {R.NC_REPEAT: 1}
    assert (await f.get(e["id"]))["selection_status"] == R.NC_REPEAT


async def test_an_so_without_an_attendance_row_follows_the_setting(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    day = str(today_local(tz_of("Asia/Kolkata")))  # settings changes apply from the day they are saved

    async def so1():
        r = await client.get("/api/v1/compliance", params={"day": day}, headers=await f("monitor"))
        return next(i for i in r.json()["items"] if i["emp_code"] == tenant_a["so1_code"])

    assert (await so1())["state"] == "no attendance"
    r = await client.patch("/api/v1/settings", headers=await f("admin"), json={"unmarked_attendance": "absent"})
    assert r.status_code == 200, r.text
    row = await so1()
    assert (row["state"], row["shortfall"]) == ("absent", "AB")


async def test_upload_problems_say_where_what_and_how_to_fix(client, tenant_a):
    f = Flow(client, tenant_a)

    def upload(text):
        return {"file": ("people.csv", text.encode(), "text/csv")}

    r = await client.post("/api/v1/imports/roster", headers=await f("monitor"), files=upload("Emp Code,Full Name\nX1,Asha\n"),
                          data={"dry_run": "true"})
    assert r.status_code == 200  # "Emp Code" and "Full Name" are accepted spellings
    r = await client.post("/api/v1/imports/roster", headers=await f("monitor"), files=upload("Code,Person\nX1,Asha\n"),
                          data={"dry_run": "true"})
    assert r.status_code == 422
    assert "missing the columns 'Emp ID', 'Name'" in r.json()["detail"] and "'Code', 'Person'" in r.json()["detail"]
    csv = "Emp ID,Name,Designation,Branch,Joining date\nY1,Asha,RO,Brnch One,31-02-2026\n"
    d = (await client.post("/api/v1/imports/roster", headers=await f("monitor"), files=upload(csv), data={"dry_run": "true"})).json()
    errs = {(e["column"], e["value"]): e["message"] for e in d["errors"]}
    assert "Did you mean 'Branch One'" in errs[("Branch", "Brnch One")]
    assert errs[("Joining date", "31-02-2026")].startswith("'31-02-2026' is not a date. Write it as DD-MM-YYYY")
    d = (await client.post("/api/v1/imports/attendance", headers=await f("monitor"), data={"dry_run": "true"},
                           files=upload("Emp ID,Date,Status\nNOBODY,2026-10-21,P\n"))).json()
    assert d["errors"] == [{"row": 2, "column": "Emp ID", "value": "NOBODY", "emp_code": "NOBODY",
                            "message": "This Emp ID is not on the employee roster. Upload the roster first, or correct the Emp ID"}]


@pytest.mark.parametrize("kw, shown", [
    ({"status": R.IN_RETRY, "lead_outcome": R.LOGGED_IN}, R.LOGGED_IN),  # the login outcome wins over the last call
    ({"status": R.IN_RETRY, "unanswered": 2}, "In retry – 2 unanswered"),
    ({"status": R.IN_RETRY, "callback_date": date(2026, 11, 12)}, "In retry – call back on 12 Nov 2026"),
    ({"status": R.IN_RETRY}, "In retry – not called yet on this number"),  # a corrected number
    ({"status": R.VALIDATED, "selection_status": R.ALLOCATE}, R.VALIDATED),
    ({"selection_status": R.NC_SPOKEN}, R.NC_SPOKEN),
    ({"selection_status": R.ALLOCATE}, R.WAITING_FIRST_CALL),
    ({"call_group": "none"}, R.NOT_CALLED_EXISTING),
    ({"call_group": "lead"}, R.WAITING_SELECTION),
])
def test_each_entry_has_one_current_status(kw, shown):
    from app.services.sankalp.engine import display_status
    args = {"status": None, "selection_status": None, "call_group": "lead", "lead_outcome": None} | kw
    assert display_status(**args) == shown


async def test_a_customer_who_is_already_a_lead_cannot_be_entered_again(client, tenant_a, clock):
    from tests.conftest import entry_body
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000051")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.CONNECTED, VISIT)
    chk = await client.get("/api/v1/entries/check-phone", params={"phone": "93000 00051"}, headers=await f("so2"))
    assert chk.json() == {"phone": "9300000051", "valid": True, "lead": None}  # validated, but no lead ID yet
    r = await client.put(f"/api/v1/calls/entries/{e['id']}/lead-card", headers=await f("caller1"),
                         json={"lead_id": "TCS-L-555001", "loan_requirement": 2_000_000})
    assert r.status_code == 200, r.text
    # any SO, any day: the phone is told while typing, and the server refuses the entry
    lead = (await client.get("/api/v1/entries/check-phone", params={"phone": "+91 93000 00051"}, headers=await f("so2"))).json()["lead"]
    assert lead["entry_code"] == e["entry_code"] and "already a lead (TCS lead ID TCS-L-555001)" in lead["message"]
    r = await client.post("/api/v1/entries", headers=await f("so2"), json=entry_body(phone="9300000051"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "already_a_lead"
    assert (await client.post("/api/v1/entries", headers=await f("so2"), json=entry_body(phone="9300000052"))).status_code == 201


async def test_bulk_entries_are_checked_like_the_phone_and_never_added_twice(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    so1, mon = tenant_a["so1_code"], await f("monitor")
    csv = ("Emp ID,Date met,Time met,Category,CP sub-type,Name of person met,Mobile number,Description\n"
           f"{so1},2026-10-20,10:30,Lead,,Asha,98490 11111,Wants a flat\n"
           f"{so1},20-10-2026,2:45 PM,Prospect,,Babu,9849022222,Plans to build next year\n"
           f"NOBODY,2026-10-20,11:00,Lead,,Chitra,9849033333,Met at the bus stand\n"
           f"{so1},2026-10-20,11:00,Builder,,Dinesh,9849044444,Unknown category\n"
           f"{so1},2026-10-20,25:00,Lead,,Esha,12345,Bad time and mobile\n")
    files = {"file": ("entries.csv", csv.encode(), "text/csv")}
    dry = (await client.post("/api/v1/imports/entries", headers=mon, files=files, data={"dry_run": "true"})).json()
    assert dry["summary"] == {"rows": 5, "new_entries": 2, "already_uploaded": 0, "errors": 3}
    errs = {(e["row"], e["column"]): (e["value"], e["message"]) for e in dry["errors"]}
    assert errs[(4, "Emp ID")][1].startswith("This Emp ID is not on the employee roster")
    assert errs[(5, "Category")][0] == "Builder" and "Lead, Prospect" in errs[(5, "Category")][1]
    assert errs[(6, "Time met")][0] == "25:00" and errs[(6, "Mobile number")][0] == "12345"
    real = (await client.post("/api/v1/imports/entries", headers=mon, files=files)).json()
    assert [c["entry_code"] for c in real["created"]] == [f"{so1}-20261020-103000", f"{so1}-20261020-144500"]
    d = await f.get((await client.get("/api/v1/entries", params={"q": "Babu"}, headers=mon)).json()["items"][0]["id"])
    assert (d["source"], d["location"]["status"], d["entry_date"], d["current_status"]) == ("import", "bulk_upload", "2026-10-20", R.WAITING_SELECTION)
    again = (await client.post("/api/v1/imports/entries", headers=mon, files=files)).json()
    assert again["summary"]["new_entries"] == 0 and again["summary"]["already_uploaded"] == 2
    # imported entries are selected and called like any other
    await f.callers(clock.day, {"b1": "caller1"})
    assert (await f.run(clock.day))["selection"] == {R.ALLOCATE: 2}
    assert (await client.post("/api/v1/imports/entries", headers=await f("bm1"), files=files)).status_code == 403


async def test_any_table_on_screen_can_be_saved_as_excel(client, tenant_a):
    import io

    from openpyxl import load_workbook
    f = Flow(client, tenant_a)
    body = {"name": "Open actions", "header": ["Entry ID", "Mobile number", "Amount"],
            "rows": [["AHFL90001-20261107-104000", "9000100001", 2500000], ["=HYPERLINK(\"x\")", None, 1.5]]}
    r = await client.post("/api/v1/exports/xlsx", headers=await f("bm1"), json=body)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxmlformats")
    ws = load_workbook(io.BytesIO(r.content)).active
    rows = [[c.value for c in row] for row in ws.iter_rows()]
    assert rows[0] == ["Entry ID", "Mobile number", "Amount"]
    assert rows[1] == ["AHFL90001-20261107-104000", "9000100001", 2500000]  # the mobile number stays text
    assert rows[2][0] == "'=HYPERLINK(\"x\")"  # a formula is never run
    assert (await client.post("/api/v1/exports/xlsx", json=body)).status_code == 401


# ---------------------------------------------------------------- aligned with Aham's Takeoff master (Excel), Nov 2026
async def test_the_mis_files_own_column_names_are_read(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000071")
    csv = ("S.No,Region,Branch,TCS ID,Emp Code,Login Date,Applicant Contact No (Customer),Product Type,Final Status\n"
           "1,AP & TG,Vijayawada,TCS-900,X,2026-10-25,9300000071,Home Loan,Sanctioned\n")
    r = await client.post("/api/v1/imports/login-register", headers=await f("mis"),
                          files={"file": ("MIS Import.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200 and r.json()["summary"]["entries_matched"] == 1, r.text
    assert (await f.get(e["id"]))["tcs_id"] == "TCS-900"


async def test_the_tracker_gives_the_branch_an_action_from_its_fixed_lists(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000081")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.CONNECTED, VISIT)
    url = f"/api/v1/calls/entries/{e['id']}/tracker"
    bad = await client.put(url, headers=await f("master"), json={"owner": "branch", "action_type": "Ring him again"})
    assert bad.status_code == 422  # the action types and reject reasons are the tracker's fixed lists
    r = await client.put(url, headers=await f("master"), json={"owner": "branch", "action_type": R.ACT_CONFIRM_LOGIN,
                                                               "followup_date": "2026-10-23"})
    assert r.status_code == 200, r.text
    d = await f.get(e["id"])
    assert (d["so_action"], d["so_action_date"], d["cc_action"]) == (R.ACT_CONFIRM_LOGIN, "2026-10-23", None)
    clock.day = date(2026, 12, 20)  # a branch item stays until the tracker changes
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    assert (await f.get(e["id"]))["so_action"] == R.ACT_CONFIRM_LOGIN
    r = await client.put(url, headers=await f("master"), json={"owner": "call_centre"})  # no date: a follow-up now
    assert (r.json().get("cc_action") or (await f.get(e["id"]))["cc_action"]) == R.CC_FOLLOW_UP
    assert (await f.get(e["id"]))["so_action"] is None
    r = await client.put(url, headers=await f("master"), json={"owner": "done", "outcome": "Rejected", "reject_reason": "Credit score"})
    assert r.status_code == 200 and (await f.get(e["id"]))["lead_outcome"] == R.OUTCOME_REJECTED


async def test_only_the_questions_that_apply_to_the_loan_need_are_kept(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    lap, bt = await f.entry("so1", phone="9300000091"), await f.entry("so1", hhmm="11:00", phone="9300000092")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    r = await f.call("caller1", lap["id"], R.CONNECTED, OK | {"loan_need": "LAP", "next_step": "SO / branch visit",
                                                              "own_contribution": "Fully"})
    assert (r["status"], r["so_action"]) == (R.NOT_COUNTED_LAP, R.ACT_FOLLOW_UP_LEAD)  # no next step asked for a LAP
    answers = (await f.get(lap["id"]))["attempts"][-1]["answers"]
    assert "next_step" not in answers and "timeline" not in answers and "own_contribution" not in answers
    await f.call("caller1", bt["id"], R.CONNECTED, OK | {"loan_need": "Balance transfer", "own_contribution": "Fully"})
    answers = (await f.get(bt["id"]))["attempts"][-1]["answers"]
    assert "own_contribution" not in answers and answers["timeline"] == OK["timeline"]


async def test_spoken_to_means_fewer_than_30_days_ago(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    first = [await f.entry("so1", hhmm=f"1{i}:00", phone=p) for i, p in enumerate(("9300000101", "9300000102"))]
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)  # 21 Oct
    for e in first:
        await f.call("caller1", e["id"], R.CONNECTED, VISIT)  # both spoken to on 21 Oct
    day29 = await f.entry("so2", day="2026-11-18", phone="9300000101")
    clock.day = date(2026, 11, 19)  # 29 days later
    await f.callers(clock.day, {"b1": "caller1", "b2": "caller1"})
    await f.run(clock.day)
    assert (await f.get(day29["id"]))["selection_status"] == R.NC_SPOKEN
    day30 = await f.entry("so2", day="2026-11-19", phone="9300000102")
    clock.day = date(2026, 11, 20)  # 30 days later: may be called again
    await f.callers(clock.day, {"b1": "caller1", "b2": "caller1"})
    await f.run(clock.day)
    assert (await f.get(day30["id"]))["selection_status"] == R.ALLOCATE


async def test_a_follow_up_goes_to_the_caller_who_created_the_lead_id(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000111")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.RNR)  # caller1 handles it first
    clock.day = date(2026, 10, 22)
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    r = await client.post("/api/v1/calls/allocations/move", headers=await f("master"),
                          json={"from_caller_id": str(tenant_a["caller1_id"]), "to_caller_id": str(tenant_a["caller2_id"])})
    assert r.status_code == 200, r.text
    await f.call("caller2", e["id"], R.CONNECTED, VISIT)
    r = await client.put(f"/api/v1/calls/entries/{e['id']}/lead-card", headers=await f("caller2"),
                         json={"lead_id": "TCS-L-1", "loan_requirement": 2_000_000})
    assert r.status_code == 200, r.text
    await client.put(f"/api/v1/calls/entries/{e['id']}/tracker", headers=await f("master"),
                     json={"owner": "call_centre", "followup_date": "2026-10-26"})
    clock.day = date(2026, 10, 26)
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    assert (await f.list("caller2"))[e["entry_code"]]["kind"] == "followup"  # not caller1, who handled it first


async def test_a_reopened_lead_is_in_retry_and_priority_until_reached(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000121")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.CONNECTED, VISIT)
    await client.post(f"/api/v1/branch/leads/{e['id']}/answer", headers=await f("bm1"), json={"code": "3"})
    d = await f.get(e["id"])
    assert (d["status"], d["priority"], d["so_action"]) == (R.IN_RETRY, True, None)
    assert d["current_status"] == "In retry – PRIORITY (Branch: customer not answering)"
    await f.call("caller1", e["id"], R.RNR)  # not reached: stays reopened, PRIORITY again tomorrow
    clock.day = date(2026, 10, 22)
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    assert (await f.list("caller1"))[e["entry_code"]]["kind"] == "priority"
    r = await f.call("caller1", e["id"], R.CONNECTED, VISIT)
    d = await f.get(e["id"])
    assert (r["status"], d["priority"], d["so_action"]) == (R.VALIDATED, False, R.ACT_VISIT)
