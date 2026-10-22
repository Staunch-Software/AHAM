"""Branch/agent analytics and map data."""
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.core.db import SessionLocal
from tests.conftest import auth, login, submission_body, upload_photo

IST = ZoneInfo("Asia/Kolkata")


async def make_world(client, tenant):
    """HQ (existing) with the fixture agent, plus branch North with its own agent. Returns ids and tokens."""
    adm = await login(client, tenant["admin_email"])
    r = await client.post("/api/v1/branches", headers=auth(adm), json={"name": "North", "code": "N1", "latitude": 13.0, "longitude": 80.2})
    assert r.status_code == 201
    north = r.json()["id"]
    email = f"north-{uuid.uuid4().hex[:6]}@x.io"
    r = await client.post("/api/v1/employees", headers=auth(adm), json={
        "employee_code": "N-AGENT", "full_name": "North Agent", "email": email, "password": "password123",
        "role": "agent", "branch_id": north, "branch_ids": [north]})
    assert r.status_code == 201, r.text
    return {"adm": adm, "ag": await login(client, tenant["agent_email"]), "ag2": await login(client, email),
            "north": north, "hq": str(tenant["branch_id"]), "ag2_id": r.json()["id"]}


async def post(client, tok, **kw):
    r = await client.post("/api/v1/submissions", json=submission_body(form_version=1, **kw), headers=auth(tok))
    assert r.status_code == 201, r.text
    return r.json()


async def test_overview_branch_and_agent_metrics(client, tenant_a, tenant_b):
    w = await make_world(client, tenant_a)
    r1, r2, r3 = [await post(client, w["ag"]) for _ in range(3)]
    n1 = await post(client, w["ag2"])
    # r1 rejected then corrected (rev 2, pending), r2 approved, r3 untouched
    await client.post(f"/api/v1/submissions/{r1['id']}/reviews", headers=auth(w["adm"]),
                      json={"decision": "rejected", "reason_code": "missing_information", "comment": "x"})
    await client.post(f"/api/v1/submissions/{r2['id']}/reviews", headers=auth(w["adm"]), json={"decision": "approved"})
    fix = await client.post("/api/v1/submissions", headers=auth(w["ag"]),
                            json=submission_body(form_version=1, corrects={"submission_id": r1["id"], "base_revision": 1}))
    assert fix.status_code == 201, fix.text

    o = (await client.get("/api/v1/analytics/overview?period=month", headers=auth(w["adm"]))).json()
    rows = {b["name"]: b for b in o["branches"]}
    hq = next(b for b in o["branches"] if b["branch_id"] == w["hq"])
    assert hq["reports"] == 3 and rows["North"]["reports"] == 1  # the correction is NOT counted as a new report
    assert hq["assigned_agents"] == 1 and hq["active_agents"] == 1 and rows["North"]["assigned_agents"] == 1
    assert (hq["pending"], hq["approved"], hq["needs_correction"]) == (2, 1, 0)  # current state of those 3 reports
    assert hq["reviewed_decisions"] == 2 and hq["rejection_rate"] == 50.0  # 1 rejected of 2 decisions; pending excluded
    assert rows["North"]["rejection_rate"] is None  # nothing reviewed yet: no rate rather than 0%
    assert o["totals"]["reports"] == 4 and o["totals"]["pending"] == 3 and o["totals"]["rejection_rate"] == 50.0
    assert o["period"]["key"] == "month" and o["period"]["timezone"] == "Asia/Kolkata" and o["period"]["targets_apply"] is True

    # targets: optional; achievement = reports / target; only for week/month
    assert hq["target"] is None and hq["achievement"] is None
    put = await client.put("/api/v1/analytics/targets", headers=auth(w["adm"]),
                           json={"scope": "branch", "id": w["hq"], "period": "monthly", "target": 4})
    assert put.status_code == 200
    o = (await client.get("/api/v1/analytics/overview?period=month", headers=auth(w["adm"]))).json()
    hq = next(b for b in o["branches"] if b["branch_id"] == w["hq"])
    assert hq["target"] == 4 and hq["achievement"] == 75.0
    o_today = (await client.get("/api/v1/analytics/overview?period=today", headers=auth(w["adm"]))).json()
    assert o_today["period"]["targets_apply"] is False and next(b for b in o_today["branches"] if b["branch_id"] == w["hq"])["achievement"] is None
    await client.put("/api/v1/analytics/targets", headers=auth(w["adm"]), json={"scope": "branch", "id": w["hq"], "period": "monthly", "target": None})
    o = (await client.get("/api/v1/analytics/overview?period=month", headers=auth(w["adm"]))).json()
    assert next(b for b in o["branches"] if b["branch_id"] == w["hq"])["target"] is None

    # drill-down to agents (includes an agent target)
    await client.put("/api/v1/analytics/targets", headers=auth(w["adm"]),
                     json={"scope": "agent", "id": str(tenant_a["agent_id"]), "period": "monthly", "target": 6})
    d = (await client.get(f"/api/v1/analytics/branches/{w['hq']}/agents?period=month", headers=auth(w["adm"]))).json()
    assert d["branch"]["name"] and len(d["agents"]) == 1
    a = d["agents"][0]
    assert a["reports"] == 3 and a["target"] == 6 and a["achievement"] == 50.0 and a["pending"] == 2 and a["approved"] == 1
    assert a["last_report_at"] and "sync" in d["note"].lower()
    # another company's admin sees nothing of this and cannot touch it
    other = await login(client, tenant_b["admin_email"])
    assert (await client.get(f"/api/v1/analytics/branches/{w['hq']}/agents", headers=auth(other))).status_code == 404
    assert (await client.put("/api/v1/analytics/targets", headers=auth(other),
                             json={"scope": "branch", "id": w["hq"], "period": "monthly", "target": 1})).status_code == 404
    o2 = (await client.get("/api/v1/analytics/overview", headers=auth(other))).json()
    assert o2["totals"]["reports"] == 0
    # validation + roles
    bad = await client.put("/api/v1/analytics/targets", headers=auth(w["adm"]), json={"scope": "branch", "id": w["hq"], "period": "monthly", "target": -1})
    assert bad.status_code == 422
    assert (await client.get("/api/v1/analytics/overview", headers=auth(w["ag"]))).status_code == 403
    assert (await client.get("/api/v1/analytics/overview?period=custom", headers=auth(w["adm"]))).status_code == 422
    c = await client.get("/api/v1/analytics/overview?period=custom&date_from=2000-01-01&date_to=2000-01-31", headers=auth(w["adm"]))
    assert c.status_code == 200 and c.json()["totals"]["reports"] == 0


async def test_trend_compares_with_previous_period(client, tenant_a):
    w = await make_world(client, tenant_a)
    old = await post(client, w["ag2"])
    await post(client, w["ag2"])
    await post(client, w["ag"])
    # move one of North's reports to the middle of last month
    today = datetime.now(IST).date()
    last_month_15 = datetime((today.replace(day=1) - timedelta(days=1)).replace(day=15).year,
                             (today.replace(day=1) - timedelta(days=1)).month, 15, 12, 0, tzinfo=IST)
    async with SessionLocal() as s:
        await s.execute(text("UPDATE form_submissions SET accepted_at_server = :t WHERE id = :i"), {"t": last_month_15, "i": uuid.UUID(old["id"])})
        await s.commit()
    o = (await client.get("/api/v1/analytics/overview?period=month", headers=auth(w["adm"]))).json()
    north = next(b for b in o["branches"] if b["name"] == "North")
    assert north["reports"] == 1 and north["previous_reports"] == 1 and north["trend_pct"] == 0.0
    hq = next(b for b in o["branches"] if b["branch_id"] == w["hq"])
    assert hq["previous_reports"] == 0 and hq["trend_pct"] is None  # nothing to compare with => no percentage
    assert o["totals"]["reports"] == 2 and o["totals"]["previous_reports"] == 1 and o["totals"]["trend_pct"] == 100.0


async def test_person_type_breakdown(client, tenant_a):
    import json
    from app.api.v1.forms import publish_version
    from app.models import Company
    from tests.conftest import SEED_FORM
    from tests.test_workflow import V4, types_by_label, v4_body
    async with SessionLocal() as s:
        await publish_version(s, await s.get(Company, tenant_a["company_id"]), V4, [None])
        await s.commit()
    adm, ag = await login(client, tenant_a["admin_email"]), await login(client, tenant_a["agent_email"])
    t = await types_by_label(client, adm)
    for name in ("Dealer", "Dealer", "Customer"):
        r = await client.post("/api/v1/submissions", json=v4_body(t[name]["id"]), headers=auth(ag))
        assert r.status_code == 201, r.text
    o = (await client.get("/api/v1/analytics/overview?period=month", headers=auth(adm))).json()
    assert {p["label"]: p["meetings"] for p in o["person_types"]} == {"Dealer": 2, "Customer": 1}


# ------------------------------------------------------------------ map
async def test_map_markers_filters_and_accuracy(client, tenant_a, tenant_b):
    w = await make_world(client, tenant_a)
    pid = await upload_photo(client, w["ag"], latitude=14.4426, longitude=79.9865, accuracy_m=7, location_status="obtained")
    a = await post(client, w["ag"], photo_id=pid)  # HQ, with GPS 16.5/80.6 acc 12.5
    b = await post(client, w["ag2"])  # North
    nogps = await client.post("/api/v1/submissions", headers=auth(w["ag"]),
                              json=submission_body(form_version=1, location={"status": "permission_denied"}))
    assert nogps.status_code == 201
    await client.post(f"/api/v1/submissions/{b['id']}/reviews", headers=auth(w["adm"]), json={"decision": "approved"})

    m = (await client.get("/api/v1/map/markers", headers=auth(w["adm"]))).json()
    assert m["counts"] == {"reports": 3, "with_gps": 2, "without_gps": 1, "shown": 2, "truncated": False}
    ids = {r["id"] for r in m["reports"]}
    assert ids == {a["id"], b["id"]}  # the report without GPS has no marker (but is counted)
    ra = next(r for r in m["reports"] if r["id"] == a["id"])
    assert ra["latitude"] == 16.5 and ra["longitude"] == 80.6 and ra["accuracy_m"] == 12.5
    assert ra["agent_name"] == "Agent" and ra["branch_name"] == "HQ" and ra["review_status"] == "pending"
    assert ra["reference"].startswith("FS-") and ra["meeting_dates"] == ["2026-10-10"] and "note" in m
    assert [x["name"] for x in m["branches"]] == ["North"] and m["branches"][0]["latitude"] == 13.0  # only branches with coordinates

    only_hq = (await client.get(f"/api/v1/map/markers?branch_id={w['hq']}", headers=auth(w["adm"]))).json()
    assert {r["id"] for r in only_hq["reports"]} == {a["id"]} and only_hq["branches"] == []
    appr = (await client.get("/api/v1/map/markers?review_status=approved", headers=auth(w["adm"]))).json()
    assert {r["id"] for r in appr["reports"]} == {b["id"]}
    by_agent = (await client.get(f"/api/v1/map/markers?agent_id={w['ag2_id']}", headers=auth(w["adm"]))).json()
    assert {r["id"] for r in by_agent["reports"]} == {b["id"]}
    out = (await client.get("/api/v1/map/markers?date_from=2000-01-01&date_to=2000-01-02", headers=auth(w["adm"]))).json()
    assert out["reports"] == [] and out["counts"]["reports"] == 0

    # photo locations are separate from submission locations
    withp = (await client.get("/api/v1/map/markers?include_photos=true&include_branches=false", headers=auth(w["adm"]))).json()
    assert len(withp["photos"]) == 1 and withp["photos"][0]["latitude"] == 14.4426 and withp["photos"][0]["submission_id"] == a["id"]
    assert withp["branches"] == [] and (await client.get("/api/v1/map/markers", headers=auth(w["adm"]))).json()["photos"] == []

    # isolation and roles
    other = await login(client, tenant_b["admin_email"])
    o = (await client.get("/api/v1/map/markers", headers=auth(other))).json()
    assert o["reports"] == [] and o["branches"] == [] and o["counts"]["reports"] == 0
    assert (await client.get("/api/v1/map/markers", headers=auth(w["ag"]))).status_code == 403
