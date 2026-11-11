"""Weighted average IRR through the API: the register upload, both reports, detail, reconciliation, exceptions,
settings, exports and the data scope. The formula itself is tested in test_irr_calc.py."""
import csv
import io

import pytest_asyncio
from openpyxl import load_workbook
from sqlalchemy import select

from tests.conftest import as_, make_company

HEADER = ("Loan account number,Disbursement reference,Disbursement date,Product,Branch,Disbursed amount,"
          "Tenure in months,ROI %,Status,Customer name\n")
# B1 = Branch One (region One), B2 = Branch Two (region One), B3 = Branch Three (region Two)
REGISTER = HEADER + (
    "HLA,1,05-11-2026,Home Loan,B1,3000000,240,9,Disbursed,A\n"  # the BRD example with HLB: 9.12
    "HLB,1,05-11-2026,Home Loan,Branch One,500000,60,12,,B\n"
    "HLC,1,02-11-2026,Home Loan,B3,1000000,120,10,,C\n"
    "HLA,2,15-10-2026,Home Loan,B1,1000000,240,9,,A\n"  # second tranche of HLA, last month
    "HLD,,31-03-2026,Home Loan,B2,2000000,180,8.5,,D\n"  # last financial year
    "HLE,1,05-11-2026,Home Loan,B1,900000,240,7,CANCELLED,E\n"  # excluded
    "HLF,1,05-11-2026,Home Loan,B2,700000,,9.5,,F\n"  # exception: no tenure
    "LAP1,1,05-11-2026,LAP,B1,500000,60,12,,G\n"
    "LAP2,1,03-11-2026,Loan Against Property,B3,800000,84,13,,H\n"
)
DAY = "2026-11-05"


def _file(text: str, name: str = "register.csv") -> dict:
    return {"file": (name, text.encode(), "text/csv")}


async def _upload(client, h, text=REGISTER, dry=False, name="register.csv"):
    return await client.post("/api/v1/irr/disbursements", headers=h, files=_file(text, name),
                             data={"dry_run": str(dry).lower()})


@pytest_asyncio.fixture
async def loaded(client):
    t = await make_company()
    r = await _upload(client, await as_(client, t, "mis"))
    assert r.status_code == 200, r.text
    return t


def _rows(body) -> dict:
    return {r["label"]: r for r in body["rows"]}


async def test_dry_run_saves_nothing_then_upload_and_reupload_never_double_counts(client):
    t = await make_company()
    mis = await as_(client, t, "mis")
    dry = await _upload(client, mis, dry=True)
    assert dry.status_code == 200, dry.text
    assert dry.json()["summary"] == {"rows": 9, "new": 9, "replaced": 0, "excluded": 1, "exceptions": 1, "errors": 0}
    assert dry.json()["columns"]["Disbursed amount"] == "Disbursed amount"
    assert (await client.get("/api/v1/irr/uploads", headers=mis)).json() == []
    rep = (await client.get(f"/api/v1/irr/report?as_of={DAY}&level=company", headers=mis)).json()
    assert rep["total"]["periods"]["YTD"]["accounts"] == 0 and rep["total"]["periods"]["YTD"]["irr"] is None

    first = (await _upload(client, mis)).json()
    assert first["summary"]["new"] == 9 and first["batch_id"]
    again = (await _upload(client, mis)).json()
    assert again["summary"] == {"rows": 9, "new": 0, "replaced": 9, "excluded": 1, "exceptions": 1, "errors": 0}
    hist = (await client.get("/api/v1/irr/uploads", headers=mis)).json()
    assert len(hist) == 2 and hist[0]["summary"]["replaced"] == 9
    rep = (await client.get(f"/api/v1/irr/report?as_of={DAY}&level=company", headers=mis)).json()
    assert rep["total"]["periods"]["YTD"] == {"accounts": 3, "irr": 9.19, "amount": 5500000.0, "records": 4}


async def test_report_today_month_year_by_branch(client, loaded):
    h = await as_(client, loaded, "pm")
    r = await client.get(f"/api/v1/irr/report?as_of={DAY}&product=HL&level=branch", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    rows = _rows(body)
    assert list(rows) == ["Branch One", "Branch Two", "Branch Three"]  # region One first, then region Two
    b1 = rows["Branch One"]["periods"]
    assert (b1["TD"]["accounts"], b1["TD"]["irr"]) == (2, 9.12)  # the BRD example
    assert (b1["MTD"]["accounts"], b1["MTD"]["irr"]) == (2, 9.12)
    assert (b1["YTD"]["accounts"], b1["YTD"]["irr"]) == (2, 9.09)  # HLA's two tranches count once
    b2 = rows["Branch Two"]["periods"]
    assert b2["YTD"] == {"accounts": 0, "irr": None, "amount": 0.0, "records": 0}  # HLD is last year, HLF an exception
    b3 = rows["Branch Three"]["periods"]
    assert b3["TD"]["irr"] is None and b3["MTD"]["irr"] == 10.0
    total = body["total"]
    assert total["label"] == "Company total"
    assert [(total["periods"][p]["accounts"], total["periods"][p]["irr"]) for p in ("TD", "MTD", "YTD")] == [
        (2, 9.12), (3, 9.24), (3, 9.19)]  # from the loans: 8040/870 and 10200/1110, not an average of the rows
    assert body["open_exceptions"] == {"TD": 1, "MTD": 1, "YTD": 1}
    assert body["periods"]["YTD"] == {"from": "2026-04-01", "to": DAY}
    # region level and the default day (the latest disbursement)
    reg = (await client.get("/api/v1/irr/report?product=NHL&level=region", headers=h)).json()
    assert reg["as_of"] == DAY
    assert {k: v["periods"]["MTD"]["irr"] for k, v in _rows(reg).items()} == {"Region One": 12.0, "Region Two": 13.0}
    assert reg["total"]["periods"]["MTD"]["irr"] == 12.69


async def test_financial_year_boundary_31_march_and_1_april(client, loaded):
    h = await as_(client, loaded, "admin")
    mar = (await client.get("/api/v1/irr/report?as_of=2026-03-31&level=company", headers=h)).json()
    assert mar["total"]["periods"]["YTD"]["accounts"] == 1 and mar["total"]["periods"]["YTD"]["irr"] == 8.5
    apr = (await client.get("/api/v1/irr/report?as_of=2026-04-01&level=company", headers=h)).json()
    assert apr["total"]["periods"]["YTD"]["accounts"] == 0 and apr["total"]["periods"]["YTD"]["irr"] is None


async def test_month_by_product(client, loaded):
    h = await as_(client, loaded, "bizm")
    body = (await client.get(f"/api/v1/irr/report/month-by-product?as_of={DAY}&level=region", headers=h)).json()
    rows = _rows(body)
    assert rows["Region One"]["classes"]["HL"]["irr"] == 9.12 and rows["Region One"]["classes"]["NHL"]["irr"] == 12.0
    assert rows["Region Two"]["classes"]["HL"]["accounts"] == 1 and rows["Region Two"]["classes"]["NHL"]["irr"] == 13.0
    assert body["total"]["classes"]["HL"] == {"accounts": 3, "irr": 9.24, "amount": 4500000.0, "records": 3}
    assert body["total"]["classes"]["NHL"]["irr"] == 12.69 and body["open_exceptions"] == 1


async def test_row_errors_are_exact_and_file_problems_are_named(client):
    t = await make_company()
    mis = await as_(client, t, "mis")
    bad = (HEADER.replace("Disbursed amount", "Disbursed Amount (Rs)") +
           "OK1,1,01-11-2026,Home Loan,B1,100000,120,9,,\n" * 1 +
           "OK2,1,01-11-2026,Home Loan,B1,100000,120,9,,\n"
           "OK3,1,01-11-2026,Home Loan,B1,100000,120,9,,\n"
           "OK4,1,01-11-2026,Home Loan,B1,100000,120,9,,\n"
           "OK5,1,01-11-2026,Home Loan,B1,100000,120,9,,\n"
           "BAD1,1,31/02/2026,Home Loan,B1,100000,120,9,,\n"  # row 7
           "BAD2,1,01-11-2026,Gold Loan,Nowhere,\"30,00,000\",240,950,,\n")  # row 8
    r = await _upload(client, mis, bad, dry=True)
    assert r.status_code == 200, r.text
    errs = r.json()["errors"]
    assert errs[0] == {"row": 7, "column": "Disbursement date", "value": "31/02/2026",
                       "message": "Not a real date. Use DD-MM-YYYY, for example 05-11-2026"}
    row8 = {e["column"]: e for e in errs if e["row"] == 8}
    assert set(row8) == {"Product", "Branch", "ROI %"}  # "30,00,000" is a fine amount
    assert row8["Branch"]["value"] == "Nowhere" and "HR & Admin > Organization" in row8["Branch"]["message"]
    assert row8["ROI %"]["message"] == "Too high for a rate of interest. Enter the rate as a percentage, for example 9.25"
    assert r.json()["summary"]["errors"] == 2 and r.json()["summary"]["new"] == 5

    missing = await _upload(client, mis, "LAN,Date,Product,Amount,Tenure\nX,01-11-2026,LAP,1,1\n")
    assert missing.status_code == 422
    assert missing.json()["detail"] == (
        "Missing columns: Branch, ROI %. Columns found in the file: 'LAN', 'Date', 'Product', 'Amount', 'Tenure'. "
        "Download the template for the expected headings.")
    assert (await _upload(client, mis, "x", name="register.pdf")).status_code == 422
    assert "no disbursements" in (await _upload(client, mis, HEADER)).json()["detail"]
    assert (await client.get("/api/v1/irr/uploads", headers=mis)).json() == []  # nothing saved by any of these


async def test_xlsx_upload_and_template(client):
    t = await make_company()
    mis = await as_(client, t, "mis")
    tpl = await client.get("/api/v1/irr/disbursements/template?format=xlsx", headers=mis)
    assert tpl.status_code == 200
    ws = load_workbook(io.BytesIO(tpl.content)).active
    assert ws["A1"].value == "Loan account number" and ws["H1"].value == "ROI %"
    ws["E2"], ws["E3"] = "B1", "B2"  # the template's example branch is not in this company
    buf = io.BytesIO()
    ws.parent.save(buf)
    r = await client.post("/api/v1/irr/disbursements", headers=mis, files={"file": ("reg.xlsx", buf.getvalue(), "application/octet-stream")})
    assert r.status_code == 200, r.text
    assert r.json()["summary"] == {"rows": 2, "new": 2, "replaced": 0, "excluded": 0, "exceptions": 0, "errors": 0}


async def test_scope_and_permissions(client, loaded):
    t = loaded
    bm = await as_(client, t, "bm1")
    rep = (await client.get(f"/api/v1/irr/report?as_of={DAY}", headers=bm)).json()
    assert list(_rows(rep)) == ["Branch One"] and rep["total"]["label"] == "Total"
    assert rep["total"]["periods"]["MTD"]["irr"] == 9.12  # Branch One only
    other = (await client.get(f"/api/v1/irr/detail?as_of={DAY}&period=YTD&branch_id={t['b3']}", headers=bm)).json()
    assert other["total"] == 0  # another branch's loans are never shown
    rm = await as_(client, t, "rm1")
    assert list(_rows((await client.get(f"/api/v1/irr/report?as_of={DAY}", headers=rm)).json())) == ["Branch One", "Branch Two"]
    for key in ("caller1", "so1", "master", "monitor"):
        h = await as_(client, t, key)
        assert (await client.get("/api/v1/irr/report", headers=h)).status_code == 403, key
    for key in ("bm1", "pm"):
        h = await as_(client, t, key)
        assert (await _upload(client, h, dry=True)).status_code == 403
        assert (await client.put("/api/v1/irr/settings", headers=h, json={})).status_code == 403


async def test_detail_and_exports(client, loaded):
    t = loaded
    h = await as_(client, t, "mis")
    q = f"as_of={DAY}&period=YTD&product=HL&branch_id={t['b1']}"
    d = (await client.get(f"/api/v1/irr/detail?{q}&page_size=2", headers=h)).json()
    assert d["total"] == 3 and len(d["items"]) == 2
    assert d["totals"] == {"records": 3, "accounts": 2, "amount": 4500000.0, "weight": 990000000.0,
                           "weighted_roi": 9000000000.0, "irr": 9.09}
    first = d["items"][0]
    assert first["loan_account"] == "HLA" and first["weight"] == 240000000.0 and first["weighted_roi"] == 2160000000.0

    out = await client.get(f"/api/v1/irr/detail?{q}&format=csv", headers=h)
    assert out.headers["content-type"].startswith("text/csv") and "attachment" in out.headers["content-disposition"]
    lines = list(csv.reader(io.StringIO(out.content.decode("utf-8-sig"))))
    assert lines[0][0] == "Loan account number" and len(lines) == 4
    assert lines[1][:3] == ["HLA", "2", "15-10-2026"] and lines[1][-1] == "2160000000"

    x = await client.get(f"/api/v1/irr/report?as_of={DAY}&format=xlsx", headers=h)
    ws = load_workbook(io.BytesIO(x.content)).active
    header = [c.value for c in ws[1]]
    assert header[:5] == ["Branch code", "Branch", "Region", "Today (TD): Number of loan accounts",
                          "Today (TD): Weighted average IRR (%)"]
    last = [c.value for c in ws[ws.max_row]]
    assert last[1] == "Company total" and last[3:5] == [2, 9.12]
    c = await client.get(f"/api/v1/irr/report/month-by-product?as_of={DAY}&level=company&format=csv", headers=h)
    assert list(csv.reader(io.StringIO(c.content.decode("utf-8-sig"))))[1] == ["Company total", "3", "9.24", "2", "12.69"]


async def test_exceptions_are_listed_corrected_with_audit_then_counted(client, loaded):
    from app.core.db import SessionLocal
    from app.models import AuditLog

    t = loaded
    mis, bm = await as_(client, t, "mis"), await as_(client, t, "bm1")
    ex = (await client.get("/api/v1/irr/exceptions", headers=mis)).json()
    assert ex["total"] == 1 and ex["items"][0]["loan_account"] == "HLF" and ex["items"][0]["problem"] == "Tenure missing"
    eid = ex["items"][0]["id"]
    assert (await client.patch(f"/api/v1/irr/exceptions/{eid}", headers=bm, json={"tenure_months": 240})).status_code == 403
    assert (await client.patch(f"/api/v1/irr/exceptions/{eid}", headers=mis, json={"tenure_months": 0})).status_code == 422
    r = await client.patch(f"/api/v1/irr/exceptions/{eid}", headers=mis, json={"tenure_months": 240})
    assert r.status_code == 200 and r.json()["problem"] is None and r.json()["corrected_at"]
    rep = (await client.get(f"/api/v1/irr/report?as_of={DAY}", headers=mis)).json()
    assert _rows(rep)["Branch Two"]["periods"]["TD"] == {"accounts": 1, "irr": 9.5, "amount": 700000.0, "records": 1}
    assert rep["open_exceptions"]["TD"] == 0
    assert (await client.get("/api/v1/irr/exceptions?status=corrected", headers=mis)).json()["total"] == 1
    async with SessionLocal() as s:
        log = (await s.execute(select(AuditLog).where(AuditLog.action == "irr.exception.correct",
                                                      AuditLog.entity_id == eid))).scalar_one()
    assert log.details["old"]["tenure_months"] is None and log.details["new"]["tenure_months"] == 240.0
    # the next upload of the same row wins again (latest upload wins)
    await _upload(client, mis)
    assert (await client.get("/api/v1/irr/exceptions", headers=mis)).json()["total"] == 1


async def test_settings_mapping_bands_and_reclassify(client, loaded):
    t = loaded
    admin = await as_(client, t, "admin")
    s = (await client.get("/api/v1/irr/settings", headers=admin)).json()
    assert s == {"product_map": {"Home Loan": "HL", "LAP": "NHL", "Loan Against Property": "NHL"}, "bands": {},
                 "fy_start_month": 4, "decimals": 2}
    bad = {**s, "product_map": {"Home Loan": "HL", "home-loan": "NHL"}}
    assert (await client.put("/api/v1/irr/settings", headers=admin, json=bad)).status_code == 422
    assert (await client.put("/api/v1/irr/settings", headers=admin,
                             json={**s, "bands": {"HL": {"min": 12, "max": 9}}})).status_code == 422
    new = {**s, "product_map": {**s["product_map"], "Gold Loan": "NHL"}, "bands": {"HL": {"min": 9.5, "max": 14}},
           "decimals": 3}
    r = await client.put("/api/v1/irr/settings", headers=admin, json=new)
    assert r.status_code == 200 and r.json()["reclassified"] == 0
    rep = (await client.get(f"/api/v1/irr/report?as_of={DAY}", headers=admin)).json()
    assert _rows(rep)["Branch One"]["periods"]["YTD"]["irr"] == 9.091 and _rows(rep)["Branch One"]["flags"] == ["TD", "MTD", "YTD"]
    assert "Branch One, Today (TD): 9.120% is below the expected HL range of 9.500% to 14.000%" in rep["warnings"]
    gold = HEADER + "GL1,1,04-11-2026,gold loan,B1,100000,12,15,,\n"
    assert (await _upload(client, await as_(client, t, "mis"), gold)).json()["summary"]["errors"] == 0
    # LAP moves to HL: the rows already uploaded follow
    r = await client.put("/api/v1/irr/settings", headers=admin, json={**new, "product_map": {**new["product_map"], "LAP": "HL"}})
    assert r.json()["reclassified"] == 1
    nhl = (await client.get(f"/api/v1/irr/report?as_of={DAY}&product=NHL&level=company", headers=admin)).json()
    assert nhl["total"]["periods"]["MTD"]["accounts"] == 2  # Loan Against Property + Gold Loan


async def test_reconciliation_totals_agree(client, loaded):
    h = await as_(client, loaded, "mis")
    r = (await client.get("/api/v1/irr/reconciliation?date_from=2026-04-01&date_to=2026-11-05", headers=h)).json()
    tot = r["total"]
    assert (tot["rows"], tot["included"], tot["excluded"], tot["exceptions"], tot["accounts"]) == (8, 6, 1, 1, 5)
    assert tot["amount"] == 6800000.0
    assert all(c["ok"] for c in r["checks"]), r["checks"]
    assert sum(b["rows"] for b in r["branches"]) == sum(x["rows"] for x in r["regions"]) == tot["rows"]
    default = (await client.get("/api/v1/irr/reconciliation", headers=h)).json()
    assert (default["from"], default["to"]) == ("2026-11-01", DAY)
    x = await client.get("/api/v1/irr/reconciliation?date_from=2026-04-01&date_to=2026-11-05&format=xlsx", headers=h)
    ws = load_workbook(io.BytesIO(x.content)).active
    lines = [[c.value for c in row] for row in ws.iter_rows(min_row=2)]
    assert next(v for v in lines if v[0] == "Company")[:5] == ["Company", None, "Company total", None, 8]
    assert [v[2] for v in lines if v[0] in ("Month", "Year to date")] == ["Oct 2026", "Nov 2026", "Year to date (from 01-04-2026)"]


async def test_year_to_date_equals_the_sum_of_its_months(client, loaded):
    # BRD 6, YTD validation: the year's numerator and denominator against the sum of the months
    h = await as_(client, loaded, "mis")
    r = (await client.get(f"/api/v1/irr/reconciliation?date_to={DAY}", headers=h)).json()
    check = next(c for c in r["checks"] if c["name"].startswith("Year to date"))
    assert check == {"name": "Year to date (01-04-2026 to 05-11-2026) = sum of its months", "ok": True,
                     "detail": "Numerator and denominator agree"}
    months, year = r["months"], r["year"]
    assert [m["label"] for m in months] == ["Oct 2026", "Nov 2026"]  # HLD (31 Mar) is last financial year
    assert sum(m["weight"] for m in months) == year["weight"] == 1_000_000 * 240 + 967_200_000
    assert sum(m["weighted_roi"] for m in months) == year["weighted_roi"]
    assert [m["included"] for m in months] == [1, 5] and year["included"] == 6
    assert [m["accounts"] for m in months] == [1, 5] and year["accounts"] == 5  # HLA's two tranches: once in the year
    hl = (await client.get(f"/api/v1/irr/reconciliation?date_to={DAY}&product=NHL", headers=h)).json()
    assert [m["label"] for m in hl["months"]] == ["Nov 2026"] and all(c["ok"] for c in hl["checks"])
