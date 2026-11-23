"""Caller allocation by language, absence and a daily limit (app/services/sankalp/callers.py and the call-centre API)."""
from datetime import date

import pytest

from app.services.sankalp import callers as CL
from app.services.sankalp import rules as R
from tests.test_calling_flow import Flow

B, C = CL.BranchToday, CL.CallerToday


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


# ---------------------------------------------------------------- the rules
def test_a_caller_takes_a_branch_when_they_share_a_language():
    assert CL.speaks(["Tamil"], ["tamil"]) and CL.speaks(["Telugu", "Tamil"], ["Tamil"])
    assert not CL.speaks(["Telugu"], ["Tamil"])
    assert CL.speaks(["Tamil"], [])  # no language set on the branch: anyone
    assert not CL.speaks([], ["Tamil"])  # a caller with no languages is never matched


def test_auto_assign_keeps_the_usual_caller_and_otherwise_spreads_by_room():
    jaya = C("jaya", "Jaya", ["Telugu"], absent=True)
    raji = C("raji", "Raji", ["Telugu", "Tamil"], load=10)
    sita = C("sita", "Sita", ["Telugu"], load=20)
    john = C("john", "John", ["Tamil"])
    branches = [B("ank", "Anakapalli", "AP", ["Telugu"], "jaya", None, waiting=25),
                B("vja", "Vijayawada", "AP", ["Telugu"], "jaya", None, waiting=24),
                B("try", "Trichy", "RoTN T", ["Tamil"], "john", None, waiting=13),
                B("koc", "Kochi", "Kerala", ["Malayalam"], None, None, waiting=3)]
    # Jaya is absent: her largest branch to the Telugu speaker with most room (Raji, 90), the next to Sita (80 left
    # once Raji has 35); Trichy stays with John; nobody speaks Malayalam
    assert CL.auto_assign(branches, [jaya, raji, sita, john], 100) == {"ank": "raji", "vja": "sita", "try": "john", "koc": None}


def test_the_day_plan_flags_what_needs_a_change_and_suggests_who_can_take_it():
    raji = C("raji", "Raji", ["Telugu", "Tamil"], load=40)  # after the run: 40 entries on her list today
    jaya = C("jaya", "Jaya", ["Telugu"])
    john = C("john", "John", ["Tamil"], absent=True)
    branches = [B("vja", "Vijayawada", "AP", ["Telugu"], "raji", "raji", fresh_open={"raji": 30}),
                B("gnt", "Guntur", "AP", ["Telugu"], "raji", "raji", fresh_open={"raji": 10}),
                B("try", "Trichy", "RoTN T", ["Tamil"], "john", "john"),
                B("blr", "Bengaluru", "Karnataka", ["Kannada"], "raji", "raji"),
                B("hsr", "Hosur", None, [], None, None, waiting=4)]
    plan = CL.day_plan(branches, [raji, jaya, john], limit=25)
    rows = {r["branch"].id: r for r in plan["branches"]}
    assert {k: [f["code"] for f in r["flags"]] for k, r in rows.items()} == {
        "vja": ["over_limit"], "gnt": ["over_limit"], "try": ["absent"], "blr": ["language", "over_limit"],
        "hsr": ["no_caller"]}
    assert rows["try"]["flags"][0]["message"] == "John is absent today – change the caller"
    assert rows["hsr"]["flags"][0]["message"] == "No caller – 4 new entries are not allocated"
    assert {k: r["suggestion"].id if r["suggestion"] else None for k, r in rows.items()} == {
        "vja": None, "gnt": None, "try": "raji", "blr": None, "hsr": "jaya"}
    # Raji is 15 over: 15 of Vijayawada's new entries (not called yet) can go to Jaya, who speaks Telugu
    assert [(m["kind"], m["from"].id, m["to"].id, m["branch"].id, m["count"]) for m in plan["moves"]] == [
        ("entries", "raji", "jaya", "vja", 15)]


def test_before_the_run_a_whole_branch_is_suggested_when_its_new_entries_fit():
    raji, jaya = C("raji", "Raji", ["Telugu"]), C("jaya", "Jaya", ["Telugu"])
    branches = [B("vja", "Vijayawada", "AP", ["Telugu"], "raji", "raji", waiting=30),
                B("gnt", "Guntur", "AP", ["Telugu"], "raji", "raji", waiting=10)]
    plan = CL.day_plan(branches, [raji, jaya], limit=25)
    assert plan["load"] == {"raji": 40, "jaya": 0}
    # Vijayawada's 30 do not fit Jaya's 25; Guntur's 10 do
    assert [(m["kind"], m["branch"].id, m["to"].id, m["count"]) for m in plan["moves"]] == [("branch", "gnt", "jaya", 10)]


# ---------------------------------------------------------------- through the API
async def test_languages_absence_auto_assign_and_the_daily_limit(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    m = await f("master")
    b1, b2, b3 = (str(tenant_a[k]) for k in ("b1", "b2", "b3"))
    c1, c2 = str(tenant_a["caller1_id"]), str(tenant_a["caller2_id"])

    r = await client.patch(f"/api/v1/calls/callers/{c1}", headers=m, json={"languages": ["telugu"]})
    assert r.json()["languages"] == ["Telugu"]  # the spelling of the Settings list
    assert (await client.patch(f"/api/v1/calls/callers/{c2}", headers=m, json={"languages": ["Tamil", "Telugu"]})).status_code == 200
    assert (await client.patch(f"/api/v1/calls/callers/{c1}", headers=m, json={"languages": ["Klingon"]})).status_code == 422
    for b, langs, usual in ((b1, ["Telugu"], c1), (b2, ["Telugu"], c1), (b3, ["Tamil"], c2)):
        r = await client.put(f"/api/v1/calls/branches/{b}", headers=m, json={"languages": langs, "usual_caller_id": usual})
        assert r.status_code == 200, r.text
    page = (await client.get("/api/v1/calls/callers", headers=m)).json()
    by_name = {c["name"]: c for c in page["callers"]}
    assert page["limit"] == 250 and by_name["Caller1"]["usual_branches"] == ["Branch One", "Branch Two"]
    assert (await client.get("/api/v1/calls/callers", headers=await f("caller1"))).status_code == 403

    # a lead of 20 Oct, tried by Caller1 on the 21st without an answer: a retry that is Caller1's
    e1 = await f.entry("so1", day="2026-10-20", hhmm="10:00", phone="9876511111")
    await f.callers(clock.day, {"b1": "caller1"})
    await f.run(clock.day)
    await f.call("caller1", e1["id"], R.RNR)

    # the 22nd: three new entries in Branch One, and Caller1 is absent
    clock.day = date(2026, 10, 22)
    for i, hhmm in enumerate(("10:00", "11:00", "12:00")):
        await f.entry("so1", day="2026-10-21", hhmm=hhmm, phone=f"98765222{i:02d}")
    r = await client.put(f"/api/v1/calls/callers/{c1}/absence", headers=m, json={"day": "2026-10-22", "absent": True})
    assert r.status_code == 200, r.text
    plan = (await client.get("/api/v1/calls/day-plan?day=2026-10-22", headers=m)).json()
    one = {b["branch"]: b for b in plan["branches"]}["Branch One"]
    assert ([fl["code"] for fl in one["flags"]], one["waiting"], one["suggestion"]["caller"]) == (["absent"], 3, "Caller2")

    auto = (await client.post("/api/v1/calls/caller-days/auto", headers=m, json={"day": "2026-10-22"})).json()
    assert auto["auto"] == {"assigned": 3, "no_caller": []}
    assert {i["branch"]: i["caller_id"] for i in auto["items"]} == {"Branch One": c2, "Branch Two": c2, "Branch Three": c2}
    await f.run(clock.day)
    two = await f.list("caller2")
    assert len(two) == 4 and two[e1["entry_code"]]["kind"] == "retry"  # the absent caller's retry, and the new entries
    assert await f.list("caller1") == {}

    # the limit: Caller2 has 4 against 2; with Caller1 back, 2 new entries of Branch One can go to Caller1
    assert (await client.patch("/api/v1/settings", headers=await f("admin"), json={"caller_daily_limit": 2})).status_code == 200
    await client.put(f"/api/v1/calls/callers/{c1}/absence", headers=m, json={"day": "2026-10-22", "absent": False})
    plan = (await client.get("/api/v1/calls/day-plan?day=2026-10-22", headers=m)).json()
    who = {c["name"]: c for c in plan["callers"]}
    assert (who["Caller2"]["load"], who["Caller2"]["over"], who["Caller1"]["room"]) == (4, 2, 2)
    assert [(x["kind"], x["from"], x["to"], x["branch"], x["count"]) for x in plan["moves"]] == [
        ("entries", "Caller2", "Caller1", "Branch One", 2)]
    mv = await client.post("/api/v1/calls/allocations/move", headers=m,
                           json={"from_caller_id": c2, "to_caller_id": c1, "branch_id": b1, "count": 2})
    assert mv.json() == {"moved": 2}
    one, two = await f.list("caller1"), await f.list("caller2")
    assert len(one) == 2 and {v["kind"] for v in one.values()} == {"fresh"}
    assert e1["entry_code"] in two and len(two) == 2  # the retry is not moved by a limit move
