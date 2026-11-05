"""The Sankalp flow through the API: entry -> daily run -> caller's list -> calls -> lead card -> branch -> login."""
from datetime import date

import pytest

from app.services.sankalp import rules as R
from tests.conftest import as_, make_entry

OK = {"name_check": "Same person", "visit": "Yes", "relationship": "No", "loan_need": "Home purchase",
      "documents": "Yes", "timeline": "1–3 months", "income": "Salaried"}


@pytest.fixture
def clock(monkeypatch):
    """Moves the company's "today" for the call-centre code (calls, runs, windows)."""

    class Clock:
        day = date(2026, 10, 21)

    c = Clock()

    async def fake_today(s, company_id):
        return c.day

    for mod in ("app.services.sankalp.ops", "app.services.sankalp.handoff", "app.api.v1.calling", "app.api.v1.branch",
                "app.api.v1.reports", "app.api.v1.entries"):
        monkeypatch.setattr(f"{mod}.company_today", fake_today)
    return c


class Flow:
    def __init__(self, client, t):
        self.c, self.t, self.h = client, t, {}

    async def __call__(self, key):
        if key not in self.h:
            self.h[key] = await as_(self.c, self.t, key)
        return self.h[key]

    async def entry(self, so, day="2026-10-20", hhmm="10:00", phone="9876543210", category="lead", **over):
        return await make_entry(self.c, await self(so), submitted_at_device=f"{day}T{hhmm}:00+05:30", phone=phone,
                                category=category, **over)

    async def callers(self, day, mapping):
        r = await self.c.put("/api/v1/calls/caller-days", headers=await self("master"), json={
            "day": str(day), "assignments": [{"branch_id": str(self.t[b]), "caller_id": str(self.t[f"{c}_id"])}
                                             for b, c in mapping.items()]})
        assert r.status_code == 200, r.text

    async def run(self, day):
        r = await self.c.post("/api/v1/calls/runs", headers=await self("master"), json={"run_date": str(day)})
        assert r.status_code == 200, r.text
        return r.json()

    async def list(self, caller):
        r = await self.c.get("/api/v1/calls/my-list", headers=await self(caller))
        assert r.status_code == 200, r.text
        return {i["entry_code"]: i for i in r.json()["items"]}

    async def call(self, caller, eid, outcome=R.CONNECTED, answers=None, slot="10-11", next_date=None, expect=201):
        body = {"slot": slot, "outcome": outcome}
        if answers is not None:
            body["answers"] = answers
        if next_date:
            body["next_date"] = next_date
        r = await self.c.post(f"/api/v1/calls/entries/{eid}/attempts", headers=await self(caller), json=body)
        assert r.status_code == expect, r.text
        return r.json()

    async def get(self, eid, who="monitor"):
        r = await self.c.get(f"/api/v1/entries/{eid}", headers=await self(who))
        assert r.status_code == 200, r.text
        return r.json()


async def test_entry_to_login_end_to_end(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1")
    await f.callers(clock.day, {"b1": "caller1"})
    run = await f.run(clock.day)
    assert run["selection"] == {R.ALLOCATE: 1} and run["allocated"]["fresh"] == 1
    lst = await f.list("caller1")
    assert e["entry_code"] in lst and lst[e["entry_code"]]["kind"] == "fresh"
    assert (await f.list("caller2")) == {}
    await f.call("caller2", e["id"], R.RNR, expect=404)  # not in caller2's scope at all
    assert (await f.get(e["id"], "caller1"))["status"] is None  # callers see entries on their list

    # two unanswered tries today: In retry / RNR, then off today's list
    r = await f.call("caller1", e["id"], R.RNR)
    assert (r["status"], r["rag"], r["unanswered_count"]) == (R.IN_RETRY, "RNR", 1)
    assert e["entry_code"] in await f.list("caller1")
    await f.call("caller1", e["id"], R.BUSY, slot="03-04")
    assert e["entry_code"] not in await f.list("caller1")

    # next day: the retry goes back to the caller who first handled it, not the branch's new caller of the day
    clock.day = date(2026, 10, 22)
    await f.callers(clock.day, {"b1": "caller2"})
    run = await f.run(clock.day)
    assert run["allocated"] == {"retry": 1}
    assert (await f.list("caller1"))[e["entry_code"]]["kind"] == "retry"
    r = await f.call("caller1", e["id"], R.CONNECTED, OK | {"next_step": "SO / branch visit", "next_date": "2026-10-24"})
    assert (r["status"], r["rag"], r["so_action"]) == (R.VALIDATED, "GREEN", R.ACT_VISIT)
    d = await f.get(e["id"])
    assert d["customer_validated"] and d["first_validation"] and d["validated_on"] == "2026-10-22"
    assert d["so_action_date"] == "2026-10-24" and d["first_caller"] == "Caller1"

    # lead card: the loan requirement is compulsory once the lead ID is entered; the lead ID is not a login
    url = f"/api/v1/calls/entries/{e['id']}/lead-card"
    bad = await client.put(url, headers=await f("caller1"), json={"lead_id": "TCSLEAD1", "cibil_score": 750})
    assert bad.status_code == 422
    assert (await client.put(url, headers=await f("caller1"), json={"cibil_score": 950})).status_code == 422
    ok = await client.put(url, headers=await f("caller1"), json={"lead_id": "TCSLEAD1", "loan_requirement": 1_200_000,
                                                                  "cibil_score": 750, "property_pincode": "520001"})
    assert ok.status_code == 200 and ok.json()["loan_requirement"] == 1_200_000
    assert (await f.get(e["id"]))["lead_outcome"] is None

    # the branch sees the lead and answers it (14-day rule)
    leads = (await client.get("/api/v1/branch/leads", headers=await f("bm1"))).json()["items"]
    assert [i["entry_code"] for i in leads] == [e["entry_code"]]
    url = f"/api/v1/branch/leads/{e['id']}/answer"
    near = await client.post(url, headers=await f("bm1"), json={"code": "A1", "answer_date": "2026-10-30"})
    assert near.status_code == 201 and near.json()["so_action_date"] == "2026-10-30"
    assert (await client.post(url, headers=await f("bm1"), json={"code": "A1"})).status_code == 422  # date asked
    far = await client.post(url, headers=await f("bm1"), json={"code": "D", "answer_date": "2026-11-20"})
    assert far.json()["so_action"] is None and far.json()["cc_action"] == R.CC_FOLLOW_UP
    assert (await client.post(url, headers=await f("bm3"), json={"code": "B", "answer_date": "2026-10-30"})).status_code == 404

    # the login register closes the loop: matched on any of the numbers in the contact cell
    csv = "TCS ID,Customer contact,Login date,Product,Final status\nTCS0001,9000011111 / +91 98765 43210,25-10-2026,Home Loan,Logged in\n"
    r = await client.post("/api/v1/imports/login-register", headers=await f("mis"),
                          files={"file": ("register.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200 and r.json()["summary"]["entries_matched"] == 1, r.text
    d = await f.get(e["id"])
    assert (d["lead_outcome"], d["tcs_id"], d["login_date"], d["rag"]) == (R.LOGGED_IN, "TCS0001", "2026-10-25", "NA")
    assert d["sankalp_success"] and d["so_action"] is None
    await f.call("master", e["id"], R.RNR, expect=409)  # a logged-in lead is not called again

    exp = await client.get("/api/v1/takeoff/export.csv?date_from=2026-10-01&date_to=2026-10-31", headers=await f("monitor"))
    line = next(x for x in exp.text.splitlines() if e["entry_code"] in x)
    assert ",Y,Y,2026-10-22,Logged in,TCS0001,2026-10-25,Y" in line
    dash = (await client.get("/api/v1/dashboard?period=custom&date_from=2026-10-01&date_to=2026-10-31",
                             headers=await f("bm1"))).json()
    assert dash["totals"]["logged_in"] == 1 and dash["totals"]["validated"] == 1


async def test_selection_rules_in_order(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    p1, p2 = "9100000001", "9100000002"
    l1 = await f.entry("so1", "2026-10-19", phone=p1)
    l2 = await f.entry("so1", "2026-10-20", phone=p1)  # same SO, same number, within 30 days
    l3 = await f.entry("so2", "2026-10-20", "09:00", phone=p2)
    l4 = await f.entry("so3", "2026-10-20", "11:00", phone=p2)  # same number, later timestamp
    dsa = await f.entry("so3", "2026-10-20", "12:00", phone="9100000003", category="dsa_connector")
    old = await f.entry("so1", "2026-09-20", phone="9100000004")  # before the first call date
    same_day = await f.entry("so1", "2026-10-21", phone="9100000005")  # made on the run date
    existing = await f.entry("so1", "2026-10-20", phone="9100000006", category="existing_customer")
    await f.callers(clock.day, {"b1": "caller1", "b2": "caller1", "b3": "caller2"})
    run = await f.run(clock.day)
    assert run["selection"] == {R.ALLOCATE: 3, R.NC_REPEAT: 1, R.NC_DUPLICATE: 1}
    sel = {k: (await f.get(v["id"]))["selection_status"] for k, v in
           dict(l1=l1, l2=l2, l3=l3, l4=l4, dsa=dsa, old=old, same_day=same_day, existing=existing).items()}
    assert sel == {"l1": R.ALLOCATE, "l2": R.NC_REPEAT, "l3": R.ALLOCATE, "l4": R.NC_DUPLICATE, "dsa": R.ALLOCATE,
                   "old": None, "same_day": None, "existing": None}
    assert (await f.get(l2["id"]))["rag"] == "NA" and (await f.get(existing["id"]))["rag"] == "NA"
    assert (await f.run(clock.day))["selection"] == {}  # "Not called" results are final; nothing is re-run

    # spoken to within 30 days (any SO), and a number currently being called
    await f.call("caller1", l1["id"], R.CONNECTED, OK)
    await f.call("caller1", l3["id"], R.RNR)
    clock.day = date(2026, 10, 22)
    spoken = await f.entry("so2", "2026-10-21", phone=p1)
    known = await f.entry("so2", "2026-10-21", "11:00", phone=p1, category="contact_point",
                          cp_subtype_id=(await client.get("/api/v1/cp-subtypes/active", headers=await f("so2"))).json()[0]["id"])
    busy = await f.entry("so1", "2026-10-21", phone=p2)
    run = await f.run(clock.day)
    assert (await f.get(spoken["id"]))["selection_status"] == R.NC_SPOKEN
    assert (await f.get(known["id"]))["selection_status"] == R.NC_DUPLICATE  # same-day fresh duplicate comes first
    assert (await f.get(busy["id"]))["selection_status"] == R.NC_BEING_CALLED
    clock.day = date(2026, 10, 23)
    known2 = await f.entry("so3", "2026-10-22", phone=p1, category="dsa_connector")
    await f.run(clock.day)
    assert (await f.get(known2["id"]))["selection_status"] == R.NC_KNOWN  # DSA/CP: number ever spoken to


async def test_unanswered_limit_and_dsa_cp_rules(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    r = await client.patch("/api/v1/settings", headers=await f("admin"),
                           json={"max_unanswered_lead": 3, "tries_per_day_lead": 3})
    assert r.status_code == 200
    lead = await f.entry("so1", phone="9200000001")
    sub = (await client.get("/api/v1/cp-subtypes/active", headers=await f("so1"))).json()[0]["id"]
    cp = await f.entry("so1", phone="9200000002", category="contact_point", cp_subtype_id=sub)
    dsa_green = await f.entry("so1", phone="9200000003", category="dsa_connector")
    dsa_lead = await f.entry("so1", phone="9200000004", category="dsa_connector")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    for slot in ("10-11", "12-01"):
        assert (await f.call("caller1", lead["id"], R.RNR, slot=slot))["status"] == R.IN_RETRY
    r = await f.call("caller1", lead["id"], R.SWITCHED_OFF, slot="04-05")
    assert (r["status"], r["rag"]) == (R.DISCARDED_9, "RNR")
    await f.call("caller1", lead["id"], R.RNR, slot="05-06", expect=403)  # off the list now

    r = await f.call("caller1", cp["id"], R.NOT_REACHABLE)
    assert (r["status"], r["rag"]) == (R.CLOSED_NO_ANSWER, "RNR")  # DSA/CP: one try, one day
    await f.call("master", cp["id"], R.RNR, slot="11-12", expect=409)

    r = await f.call("caller1", dsa_green["id"], R.CONNECTED, {"dsa_rag": "Green", "needs_home_loan": "No"})
    assert (r["status"], r["rag"], r["so_action"]) == (R.DSA_GREEN, "GREEN", R.ACT_DSA_FOLLOWUP)
    r = await f.call("caller1", dsa_lead["id"], R.CONNECTED, OK | {"needs_home_loan": "Yes"})
    assert r["status"] == R.VALIDATED_CONVERTED and (await f.get(dsa_lead["id"]))["customer_validated"]


async def test_callback_and_answers_only_when_connected(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9300000001")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.RNR, answers=OK, expect=422)
    await f.call("caller1", e["id"], R.CALLBACK, expect=422)  # needs the date
    await f.call("caller1", e["id"], R.CALLBACK, next_date="2026-10-25", expect=422)  # a Sunday
    r = await f.call("caller1", e["id"], R.CALLBACK, next_date="2026-10-26")
    assert (r["status"], r["cc_action"], r["rag"]) == (R.IN_RETRY, R.CC_CALLBACK, "GREEN")
    clock.day = date(2026, 10, 23)
    assert (await f.run(clock.day))["allocated"] == {}  # held until the callback date
    clock.day = date(2026, 10, 26)
    assert (await f.run(clock.day))["allocated"] == {"retry": 1}


async def test_number_and_so_corrections(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9400000001")
    late = await f.entry("so1", "2026-10-01", phone="9400000002")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    r = await f.call("caller1", e["id"], R.WRONG_PERSON)
    assert (r["status"], r["rag"], r["so_action"]) == (R.AMBER_WRONG_PERSON, "AMBER", R.ACT_CORRECT_NUMBER)
    me = (await client.get("/api/v1/me/summary", headers=await f("so1"))).json()
    assert [c["entry_code"] for c in me["correct_number"]] == [e["entry_code"]]

    url = f"/api/v1/entries/{e['id']}/correct-number"
    assert (await client.post(url, headers=await f("bm3"), json={"phone": "9400000009"})).status_code == 404
    assert (await client.post(url, headers=await f("so1"), json={"phone": "9400000009"})).status_code == 403
    assert (await client.post(url, headers=await f("bm1"), json={"phone": "12345"})).status_code == 422
    r = await client.post(url, headers=await f("bm1"), json={"phone": "+91 94000 00009"})
    assert r.status_code == 200 and r.json() == {"phone": "9400000009", "status": R.IN_RETRY, "rag": "GREEN", "call_cycle": 2}
    d = await f.get(e["id"])
    assert d["entry_code"] == e["entry_code"] and d["unanswered_count"] == 0 and d["so_action"] is None
    assert any(h["kind"] == "correction.number" for h in d["history"])
    assert (await client.post(url, headers=await f("bm1"), json={"phone": "9400000008"})).status_code == 409
    clock.day = date(2026, 10, 22)
    await f.callers(clock.day, {"b1": "caller2"})
    alloc = (await f.run(clock.day))["allocated"]
    # called again automatically, by the first caller; the entry nobody called yesterday is offered again (6)
    assert alloc == {"retry": 1, "fresh": 1}
    assert (await f.list("caller1"))[e["entry_code"]]["kind"] == "retry"
    assert (await f.list("caller2"))[late["entry_code"]]["kind"] == "fresh"

    # the correction window is 15 days from the entry
    await f.call("caller2", late["id"], R.INVALID_NUMBER)
    r = await client.post(f"/api/v1/entries/{late['id']}/correct-number", headers=await f("bm1"), json={"phone": "9400000007"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "window_closed"

    # wrong SO: the RTM of the cluster corrects it; the BM of a clustered branch may not; the Entry ID stays
    url = f"/api/v1/entries/{e['id']}/correct-so"
    r = await client.post(url, headers=await f("bm1"), json={"so_user_id": str(tenant_a["so2_id"])})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "rtm_corrects"
    r = await client.post(url, headers=await f("cm1"), json={"so_user_id": str(tenant_a["so2_id"])})
    assert r.status_code == 403  # so2 is in Branch Two, outside the RTM's cluster
    r = await client.post(url, headers=await f("monitor"), json={"so_user_id": str(tenant_a["so2_id"])})
    assert r.status_code == 200 and r.json()["branch_id"] == str(tenant_a["b2"]) and r.json()["entry_code"] == e["entry_code"]
    d = await f.get(e["id"])
    assert d["so_employee_code"] == tenant_a["so2_code"] and d["emp_code"] == tenant_a["so1_code"]
    # the history names the SOs and branches, not their ids
    so_fix = next(h for h in d["history"] if h["kind"] == "correction.so")
    assert so_fix["by"] == "Monitor" and so_fix["detail"] == {"old_so": "So1", "new_so": "So2", "old_branch": "Branch One",
                                                               "new_branch": "Branch Two"}


async def test_branch_codes_rbh_priority_category_green_channel(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e2 = await f.entry("so2", phone="9500000001")  # Branch Two: no BM, so the RBH answers
    e1 = await f.entry("so1", phone="9500000002")
    gc = await f.entry("so1", phone="9500000003")
    await f.callers(clock.day, {"b1": "caller1", "b2": "caller1"})
    await f.run(clock.day)
    for e in (e1, e2):
        await f.call("caller1", e["id"], R.CONNECTED, OK)
    await f.call("caller1", gc["id"], R.CONNECTED, OK | {"loan_need": "Self-construction"})
    await client.put(f"/api/v1/calls/entries/{gc['id']}/lead-card", headers=await f("caller1"),
                     json={"loan_requirement": 700_000})

    rbh = {i["entry_code"] for i in (await client.get("/api/v1/branch/leads", headers=await f("rm1"))).json()["items"]}
    assert rbh == {e2["entry_code"]}  # Branch One has a BM, so the RBH does not answer for it
    bm = {i["entry_code"] for i in (await client.get("/api/v1/branch/leads", headers=await f("bm1"))).json()["items"]}
    assert bm == {e1["entry_code"], gc["entry_code"]}
    assert (await client.post(f"/api/v1/branch/leads/{e1['id']}/answer", headers=await f("rm1"),
                              json={"code": "R5"})).status_code == 403

    # code 3: the customer does not answer the branch -> the call centre retries at once, as PRIORITY
    r = await client.post(f"/api/v1/branch/leads/{e2['id']}/answer", headers=await f("rm1"), json={"code": "3"})
    assert r.status_code == 201 and r.json()["priority"] is True
    clock.day = date(2026, 10, 22)
    await f.run(clock.day)
    item = (await f.list("caller1"))[e2["entry_code"]]
    assert item["kind"] == "priority" and item["priority"]

    # code 2: category wrong -> the Sankalp monitor fixes it
    await client.post(f"/api/v1/branch/leads/{e1['id']}/answer", headers=await f("bm1"), json={"code": "2"})
    queue = (await client.get("/api/v1/monitor/category-review", headers=await f("monitor"))).json()["items"]
    assert [q["entry_code"] for q in queue] == [e1["entry_code"]]
    r = await client.post(f"/api/v1/monitor/category-review/{e1['id']}", headers=await f("monitor"),
                          json={"category": "prospect", "note": "Was a prospect"})
    assert r.json() == {"category": "prospect", "call_group": "lead", "category_review": "done"}

    # green channel: a branch R2/R3 on a small construction loan waits for head office
    url = f"/api/v1/branch/leads/{gc['id']}/answer"
    r = await client.post(url, headers=await f("bm1"), json={"code": "R2"})
    assert r.json()["green_channel"] == "pending" and r.json()["lead_outcome"] is None
    queue = (await client.get("/api/v1/calls/green-channel", headers=await f("master"))).json()
    assert queue[0]["entry_code"] == gc["entry_code"] and queue[0]["loan_requirement"] == 700_000
    r = await client.post(f"/api/v1/calls/green-channel/{queue[0]['answer_id']}", headers=await f("master"),
                          json={"accept_reject": False})
    assert r.json()["lead_outcome"] is None and r.json()["so_action"] == R.ACT_FOLLOW_UP_LEAD  # back to the branch
    r = await client.post(url, headers=await f("bm1"), json={"code": "R3"})
    aid = (await client.get("/api/v1/calls/green-channel", headers=await f("master"))).json()[0]["answer_id"]
    r = await client.post(f"/api/v1/calls/green-channel/{aid}", headers=await f("master"), json={"accept_reject": True})
    assert r.json()["lead_outcome"] == R.OUTCOME_REJECTED
    missed = (await client.get("/api/v1/branch/missed-dates", headers=await f("bm1"))).json()
    assert missed == []


async def test_tracker_manual_login_override_and_callback(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so1", phone="9600000001")
    other = await f.entry("so1", phone="9600000002")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e["id"], R.CONNECTED, OK | {"loan_need": "Not looking for a loan"})
    url = f"/api/v1/calls/entries/{e['id']}/tracker"
    assert (await client.put(url, headers=await f("caller1"), json={})).status_code == 403
    r = await client.put(url, headers=await f("master"), json={"rag_override": "AMBER", "notes": "Check again"})
    assert r.status_code == 200 and r.json()["rag"] == "AMBER"
    r = await client.put(url, headers=await f("master"), json={"tcs_id": "TCSMANUAL", "outcome": "Logged in"})
    assert r.json()["lead_outcome"] == R.LOGGED_IN and r.json()["tcs_id"] == "TCSMANUAL"
    d = await f.get(e["id"])
    assert d["login_source"] == "manual" and d["customer_validated"]  # a login (not LAP) validates
    r = await client.put(f"/api/v1/calls/entries/{other['id']}/tracker", headers=await f("master"),
                         json={"immediate_callback": True})
    assert r.json()["priority"] is True


async def test_login_register_rules(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    a = await f.entry("so1", "2026-10-10", phone="9700000001")
    b = await f.entry("so2", "2026-10-12", phone="9700000001")  # same customer, another SO, later
    c = await f.entry("so1", "2026-10-15", phone="9700000002")
    d = await f.entry("so1", "2026-10-15", "11:00", phone="9700000003")

    async def upload(text):
        r = await client.post("/api/v1/imports/login-register", headers=await f("master"),
                              files={"file": ("reg.csv", text.encode(), "text/csv")})
        assert r.status_code == 200, r.text
        return r.json()

    await upload("TCS ID,Customer contact,Login date,Product\n"
                 "TA,9700000001,2026-10-20,Home Loan\n"
                 "TB,9700000002,2026-10-14,Home Loan\n"  # logged in before the entry date
                 "TC,9700000003,2026-10-20,LAP\n")
    ea, eb, ec, ed = [await f.get(x["id"]) for x in (a, b, c, d)]
    assert ea["lead_outcome"] == eb["lead_outcome"] == R.LOGGED_IN
    assert ea["sankalp_success"] and not eb["sankalp_success"]  # one success per TCS ID: the earliest entry
    assert ea["customer_validated"] and eb["customer_validated"]  # both validated by the login...
    assert ea["first_validation"] and not eb["first_validation"]  # ...but paid once per customer
    assert ec["lead_outcome"] == R.LOGIN_BEFORE_ENTRY and not ec["customer_validated"]
    assert ed["lead_outcome"] == R.LOGGED_IN and ed["sankalp_success"] and not ed["customer_validated"]  # LAP

    # a later row for the same TCS ID wins: TA now belongs to another number
    await upload("TCS ID,Customer contact,Login date\nTA,9700000009,2026-10-21\n")
    ea, eb = await f.get(a["id"]), await f.get(b["id"])
    assert ea["lead_outcome"] is None and ea["tcs_id"] is None and not ea["sankalp_success"]
    dry = await client.post("/api/v1/imports/login-register", headers=await f("mis"), data={"dry_run": "true"},
                            files={"file": ("reg.csv", b"TCS ID,Customer contact\nTZ,abc\n", "text/csv")})
    assert dry.json()["dry_run"] and dry.json()["summary"]["errors"] == 1
    assert (await client.post("/api/v1/imports/login-register", headers=await f("bm1"),
                              files={"file": ("reg.csv", b"TCS ID,Customer contact\n", "text/csv")})).status_code == 403


async def test_compliance_counts_present_absent_joiners_exits(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    for i in range(3):
        await f.entry("so1", "2026-10-15", f"1{i}:00", phone=f"980000000{i}", category="lead" if i < 2 else "dsa_connector")
    await f.entry("so2", "2026-10-15", phone="9810000000")
    admin = await f("admin")
    await client.patch(f"/api/v1/employees/{tenant_a['so3_id']}", headers=admin, json={"joining_date": "2026-10-20"})
    att = f"Emp ID,Date,Status\n{tenant_a['so1_code']},2026-10-15,P(R)\n{tenant_a['so2_code']},2026-10-15,L\n"
    await client.post("/api/v1/imports/attendance", headers=await f("monitor"),
                      files={"file": ("a.csv", att.encode(), "text/csv")})
    rows = {r["emp_code"]: r for r in (await client.get("/api/v1/compliance?day=2026-10-15", headers=await f("monitor"))).json()["items"]}
    so1, so2, so3 = rows[tenant_a["so1_code"]], rows[tenant_a["so2_code"]], rows[tenant_a["so3_code"]]
    assert (so1["state"], so1["entries"], so1["lead_prospect"], so1["shortfall"], so1["lead_shortfall"]) == ("present", 3, 2, 7, 3)
    assert (so2["state"], so2["shortfall"]) == ("absent", "AB")
    assert (so3["state"], so3["shortfall"]) == ("N/A", None)
    bm_rows = (await client.get("/api/v1/compliance?day=2026-10-15", headers=await f("bm1"))).json()["items"]
    assert {r["emp_code"] for r in bm_rows} == {tenant_a["so1_code"]}  # scope
    csv = await client.get("/api/v1/compliance/export.csv?date_from=2026-10-15&date_to=2026-10-16", headers=await f("monitor"))
    assert csv.status_code == 200 and f"2026-10-15,{tenant_a['so2_code']}" in csv.text and ",AB" in csv.text
    assert (await client.get("/api/v1/compliance/export.csv?date_from=2026-10-15&date_to=2026-10-16",
                             headers=await f("bm1"))).status_code == 403


async def test_reports_map_and_unassigned_work(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    e = await f.entry("so3", phone="9900000001")
    run = await f.run(clock.day)  # no caller of the day for Branch Three
    assert run["allocated"] == {"fresh": 1, "unassigned": 1}
    over = (await client.get("/api/v1/calls/allocations?unassigned=true", headers=await f("master"))).json()
    assert over["unassigned"] == 1 and over["items"][0]["entry_code"] == e["entry_code"]
    r = await client.post(f"/api/v1/calls/allocations/{over['items'][0]['allocation_id']}/assign",
                          headers=await f("master"), json={"caller_id": str(tenant_a["caller2_id"])})
    assert r.status_code == 200 and e["entry_code"] in await f.list("caller2")
    # the Daily run page asks for unassigned work only; each caller's open count still covers their whole list
    over = (await client.get("/api/v1/calls/allocations?unassigned=true", headers=await f("master"))).json()
    assert over["unassigned"] == 0 and over["items"] == []
    assert {c["name"]: c["open"] for c in over["callers"]}["Caller2"] == 1
    await f.call("caller2", e["id"], R.RNR)
    rep = (await client.get("/api/v1/reports/callcentre?period=custom&date_from=2026-10-21&date_to=2026-10-21",
                            headers=await f("master"))).json()
    assert {c["name"]: c["attempts"] for c in rep["callers"]}.get("Caller2") == 1
    m = (await client.get("/api/v1/map/entries?period=custom&date_from=2026-10-01&date_to=2026-10-31",
                          headers=await f("bm3"))).json()
    assert m["total"] >= 1 and m["markers"][0]["lat"] == 16.5
    assert (await client.get("/api/v1/map/entries", headers=await f("caller1"))).status_code == 403
