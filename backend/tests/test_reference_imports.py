"""Settings, holidays, CP sub-types, and the roster / attendance uploads."""
from tests.conftest import as_, auth, login


async def test_settings_defaults_and_validated_patch(client, tenant_a):
    admin = await as_(client, tenant_a, "admin")
    s = (await client.get("/api/v1/settings", headers=await as_(client, tenant_a, "so1"))).json()
    assert s["takeoff_start"] == "2026-09-22" and s["first_call_date"] == "2026-09-24"
    assert (s["repeat_window_days"], s["max_unanswered_lead"], s["daily_entry_target"], s["daily_lead_target"]) == (30, 9, 10, 5)
    assert s["same_day_calling"] is False and s["duplicate_tcs_rule"] == "latest"
    r = await client.patch("/api/v1/settings", headers=admin, json={"max_unanswered_lead": 7, "same_day_calling": True})
    assert r.status_code == 200 and r.json()["max_unanswered_lead"] == 7
    assert (await client.patch("/api/v1/settings", headers=admin, json={"max_unanswered_lead": 0})).status_code == 422
    assert (await client.patch("/api/v1/settings", headers=admin, json={"nonsense": 1})).status_code == 422
    assert (await client.patch("/api/v1/settings", headers=admin,
                               json={"designation_roles": {"RO": "wizard"}})).status_code == 422


async def test_holidays(client, tenant_a):
    mon = await as_(client, tenant_a, "monitor")
    r = await client.post("/api/v1/holidays", headers=mon, json={"day": "2026-11-01", "name": "State day"})
    assert r.status_code == 201
    assert (await client.post("/api/v1/holidays", headers=mon, json={"day": "2026-11-01", "name": "Dup"})).status_code == 409
    days = (await client.get("/api/v1/holidays?year=2026", headers=mon)).json()
    assert [d["day"] for d in days] == ["2026-11-01"]
    assert (await client.delete(f"/api/v1/holidays/{r.json()['id']}", headers=mon)).status_code == 204


async def test_cp_subtype_list_management(client, tenant_a):
    admin, so = await as_(client, tenant_a, "admin"), await as_(client, tenant_a, "so1")
    r = await client.post("/api/v1/cp-subtypes", headers=admin, json={"label": "Cement dealer"})
    assert r.status_code == 201
    item = next(i for i in r.json()["items"] if i["label"] == "Cement dealer")
    assert (await client.post("/api/v1/cp-subtypes", headers=admin, json={"label": "cement DEALER"})).status_code == 409
    await client.patch(f"/api/v1/cp-subtypes/{item['id']}", headers=admin, json={"active": False})
    assert "Cement dealer" not in [s["label"] for s in (await client.get("/api/v1/cp-subtypes/active", headers=so)).json()]


def _csv(text: str) -> dict:
    return {"file": ("roster.csv", text.encode(), "text/csv")}


async def test_roster_upload_dry_run_then_save(client, tenant_a):
    mon = await as_(client, tenant_a, "monitor")
    tag = tenant_a["tag"]
    csv = ("Emp ID,Name,Designation,Region,Branch,Spoke,Joining date,Exit date\n"
           f"R1{tag},Asha,RO,Region One,Branch One,Spoke A,01-04-2026,\n"
           f"R2{tag},Babu,ABM,Region One,b2,,2026-05-10,\n"  # branch by code, ISO date
           f"R3{tag},Chitra,BM,Region One,Branch Two,,,\n"
           f"R4{tag},Dinesh,RBH,Region One,,,,\n"
           f"R5{tag},Esha,RO,Region Two,Branch One,,,\n"  # Branch One is not in Region Two
           f"R6{tag},Farid,Wizard,,Branch One,,,\n"  # unknown designation
           f"R7{tag},Gopi,RO,,Nowhere,,,\n"  # unknown branch
           f"R1{tag},Asha again,RO,,Branch One,,,\n"  # repeated Emp ID
           f"{tenant_a['so1_code']},So1 Renamed,RM,,Branch One,,,\n")  # existing person: update
    dry = await client.post("/api/v1/imports/roster", headers=mon, files=_csv(csv), data={"dry_run": "true"})
    assert dry.status_code == 200, dry.text
    d = dry.json()
    assert d["summary"] == {"created": 4, "updated": 1, "unchanged": 0, "errors": 4}
    msgs = " | ".join(e["message"] for e in d["errors"])
    assert "not Region Two" in msgs and "Wizard" in msgs and "Nowhere" in msgs and "more than once" in msgs
    # nothing saved by the dry run
    assert all(e["employee_code"] != f"R1{tag}" for e in (await client.get(
        f"/api/v1/employees?q=R1{tag}", headers=mon)).json()["items"])

    real = await client.post("/api/v1/imports/roster", headers=mon, files=_csv(csv), data={"issue_passwords": "true"})
    out = real.json()
    assert out["summary"]["created"] == 4 and len(out["credentials"]) == 4
    people = {u["employee_code"]: u for u in (await client.get("/api/v1/employees?page_size=200", headers=mon)).json()["items"]}
    asha, chitra, dinesh = people[f"R1{tag}"], people[f"R3{tag}"], people[f"R4{tag}"]
    assert asha["role"] == "sales_officer" and asha["spoke"] == "Spoke A" and asha["joining_date"] == "2026-04-01"
    assert chitra["role"] == "branch_manager" and dinesh["role"] == "region_manager" and dinesh["region_id"] == str(tenant_a["r1"])
    assert people[tenant_a["so1_code"]]["full_name"] == "So1 Renamed" and people[tenant_a["so1_code"]]["designation"] == "RM"
    # a new person signs in with the issued temporary password and must change it
    cred = next(c for c in out["credentials"] if c["emp_code"] == f"R1{tag}")
    t = await login(client, cred["emp_code"], cred["temporary_password"], portal="mobile", key="x")
    assert t["must_change_password"] is True
    hist = (await client.get("/api/v1/imports?kind=roster", headers=mon)).json()
    assert hist[0]["rows_total"] == 9 and hist[0]["rows_error"] == 4
    # without issue_passwords nobody can sign in until HR issues a temporary password
    r = await client.post("/api/v1/imports/roster", headers=mon, files=_csv(
        f"Emp ID,Name,Designation,Branch\nR8{tag},Hema,RO,Branch One\n"))
    assert r.json()["summary"]["created"] == 1 and r.json()["credentials"] == []
    no = await client.post("/api/v1/auth/login", json={"identifier": f"R8{tag}", "password": "", "portal": "mobile"})
    assert no.status_code == 422
    no = await client.post("/api/v1/auth/login", json={"identifier": f"R8{tag}", "password": "!unusable", "portal": "mobile"})
    assert no.status_code == 401


async def test_roster_never_reroles_call_centre_or_admin(client, tenant_a):
    mon = await as_(client, tenant_a, "monitor")
    r = await client.post("/api/v1/imports/roster", headers=mon, files=_csv(
        f"Emp ID,Name,Designation,Branch\n{tenant_a['caller1_code']},Caller One,RO,Branch One\n"))
    assert r.json()["summary"]["errors"] == 0
    people = (await client.get(f"/api/v1/employees?q={tenant_a['caller1_code']}", headers=mon)).json()["items"]
    assert people[0]["role"] == "caller"


async def test_attendance_long_and_wide(client, tenant_a):
    mon = await as_(client, tenant_a, "monitor")
    long = f"Emp ID,Date,Status\n{tenant_a['so1_code']},2026-10-15,P\n{tenant_a['so1_code']},16/10/2026,AB\nNOBODY,2026-10-15,P\n"
    r = await client.post("/api/v1/imports/attendance", headers=mon,
                          files={"file": ("att.csv", long.encode(), "text/csv")})
    assert r.status_code == 200 and r.json()["summary"]["marks"] == 2 and r.json()["summary"]["errors"] == 1
    wide = f"Emp ID,2026-10-15,2026-10-16,2026-10-17\n{tenant_a['so2_code']},P,P(MS),\n"
    r = await client.post("/api/v1/imports/attendance", headers=mon, files={"file": ("att.csv", wide.encode(), "text/csv")})
    assert r.json()["summary"]["marks"] == 2
    from sqlalchemy import select
    from app.core.db import SessionLocal
    from app.models import Attendance
    async with SessionLocal() as s:
        codes = dict((await s.execute(select(Attendance.day, Attendance.code).where(
            Attendance.user_id == tenant_a["so2_id"]))).all())
    assert sorted(codes.values()) == ["P", "P(MS)"]


async def test_excel_roster(client, tenant_a):
    import io
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Emp ID", "Name", "Designation", "Branch", "Joining date"])
    from datetime import datetime
    ws.append([f"X1{tenant_a['tag']}", "Excel Person", "RO", "Branch Two", datetime(2026, 6, 1)])
    buf = io.BytesIO()
    wb.save(buf)
    r = await client.post("/api/v1/imports/roster", headers=await as_(client, tenant_a, "monitor"),
                          files={"file": ("roster.xlsx", buf.getvalue(),
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200 and r.json()["summary"]["created"] == 1, r.text


async def test_only_permitted_roles_upload(client, tenant_a):
    for key in ("so1", "bm1", "caller1", "mis"):
        r = await client.post("/api/v1/imports/roster", headers=await as_(client, tenant_a, key),
                              files=_csv("Emp ID,Name\nX,Y\n"))
        assert r.status_code == 403
    assert auth  # keep import used
