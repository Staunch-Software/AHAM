"""The move from Aham's Takeoff master workbook (app/import_takeoff.py), on a small made-up workbook of the same shape."""
from datetime import date, datetime

import openpyxl
from sqlalchemy import func, select

from app import import_takeoff as T
from app.core.db import SessionLocal
from app.models import CallAttempt, Company, FollowupTracker, LeadCard, SankalpEntry, User
from app.services.sankalp import ops
from app.services.sankalp import rules as R


def serial(d: date) -> int:
    return (d - date(1899, 12, 30)).days


def workbook(path, t) -> None:
    so1, so3 = t["so1_code"], t["so3_code"]
    e1, e2, e3 = f"{so1}-20261020-100000", f"{so1}-20261020-110000", f"{so1}-20261020-120000"
    e5, e6, e7 = f"{so1}-20261020-130000", f"{so1}-20261020-140000", "UNRES-20261020-150000"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Control"
    ws.append(["Control"])
    ws.append(["Run date (the day the call sheets are for)", datetime(2026, 10, 22)])
    raw = wb.create_sheet("Raw Data")
    raw.append(["Entry ID", "Emp ID", "Name", "Region", "Branch", "Spoke", "Category", "CP Subtype", "Person Met",
                "Phone Number", "Description", "Date of Entry"])
    raw.append([e1, so1, "SO One", "Region One", "Branch One", "Spoke A", "Lead", None, "Customer A", "9876500001", "Flat", "2026-10-20"])
    raw.append([e2, so1, "SO One", "Region One", "Branch One", "Spoke A", "Lead", None, "Customer A", "9876500001", "Again", "2026-10-20"])
    raw.append([e3, so1, "SO One", "Region One", "Branch One", "Spoke A", "Contact Point", "Mason", "Mason B", "+91 98765 00003", "Site", "2026-10-20"])
    raw.append([None, so1, "SO One", "Region One", "Branch One", "Spoke A", "Lead", None, "Old C", "9876500004", "Before Takeoff", "2026-09-10"])
    raw.append([e5, so1, "SO One", "Region One", "Branch One", "Spoke A", "Lead", None, "Customer D", "12345", "Bad number", "2026-10-20"])
    raw.append([e6, so1, "SO One", "Region One", "Branch One", "Spoke A", "Existing Customer", None, "Customer E", "9876500006", "Has a loan", "2026-10-20"])
    raw.append([e7, "(Unverified - no ID)", "Someone", "Region One", "Branch One", "Spoke A", "Prospect", None, "Customer F", "9876500007", "Plot", "2026-10-20"])
    mon = wb.create_sheet("Monitor export")
    mon.append(["Entry ID", "Master status", "RAG", "SO action", "CC action", "TCS ID", "Lead outcome", "Counts as Sankalp success?"])
    mon.append([e1, "Validated", "NA", None, None, "TCS0009", "Logged in", "Yes"])
    mon.append([e2, "Not called - repeat entry by same SO", "NA", None, None, "TCS0009", "Logged in", "No"])
    mon.append([e3, "DSA/CP - Green", "GREEN", "DSA/CP follow-up", None, None, None, None])
    mon.append([e5, "Not called - no valid number", "AMBER", "Correct customer number", None, None, None, None])
    mon.append([e6, None, "NA", None, None, None, None, None])
    his = wb.create_sheet("History")
    his.append(["Caller", "Call date", "Entry ID", "Call type", "Attempt 1 slot", "Attempt 1 outcome", "Attempt 2 slot",
                "Attempt 2 outcome", "Attempt 3 slot", "Attempt 3 outcome", "DSA/CP: RAG", "DSA/CP: needs home loan himself?",
                "Name check", "Name as given", "Visit", "Relationship", "Loan need", "Timeline", "Income", "Documents",
                "Next step", "Next date", "Purpose", "Own contribution", "Remarks", "Lead ID", "Handling branch",
                "Loan requirement (Rs)", "CIBIL score"])
    his.append(["Pooja", serial(date(2026, 10, 21)), e1, "New lead", "10-11", "RNR", "03-04", "Connected", None, None, "n/a",
                "n/a", "Same person", None, "Yes", "No", "Home purchase", "1-3 months", "Salaried", "Yes", "SO / branch visit",
                serial(date(2026, 10, 23)), "Discuss eligibility", "Fully", "Keen", "TCS-L-1", "n/a", 2500000, 750])
    his.append(["Jaya", datetime(2026, 10, 21), e3, "New DSA/CP", "11-12", "Connected", None, None, None, None, "Green", "No"])
    his.append(["—", serial(date(2026, 10, 21)), e2, "Not called", None, "Not called - repeat entry by same SO"])
    logins = wb.create_sheet("Logins")
    logins.append(["S.No", "TCS ID", "Applicant Contact No (Customer)", "Login Date", "Final Status"])
    logins.append([1, "TCS0009", "9876500001", serial(date(2026, 10, 22)), "Sanctioned"])
    tr = wb.create_sheet("Follow-up tracker")
    tr.cell(1, 1, "Follow-up tracker")
    tr.cell(2, 1, "How it works")
    for c, h in enumerate(["Key", "Owner", "Action type", "Caller", "Follow-up date", "Outcome", "TCS ID", "Reject reason",
                           "RAG override", "Notes"], start=1):
        tr.cell(4, c, h)
    for c, v in enumerate([e3, "Branch", "DSA/CP follow-up", None, None, None, None, None, "Green", "Builder friend"], start=1):
        tr.cell(5, c, v)
    for c, v in enumerate(["20260910|9876500004", "Branch", "Follow up lead"], start=1):
        tr.cell(6, c, v)
    corr = wb.create_sheet("SO corrections")
    corr.append(["Entry ID", "Correct SO Emp ID", "Correct SO name", "Correct region (blank = keep)", "Correct branch (blank = keep)"])
    corr.append([e3, so3, "SO Three", None, "Branch Three"])
    wb.save(path)


async def test_takeoff_master_moves_into_the_app_and_out_again(client, tenant_a, tmp_path):
    path = tmp_path / "Takeoff_CallCentre_Master_Test.xlsx"
    workbook(path, tenant_a)
    wb = T.load_workbook(path)
    assert wb.as_of == date(2026, 10, 22) and len(wb.raw) == 7 and len(wb.tracker) == 2
    so1 = tenant_a["so1_code"]
    async with SessionLocal() as s:
        co = await s.get(Company, tenant_a["company_id"])
        actor = await s.get(User, tenant_a["master_id"])
        summary, res = await T.load(s, co, actor, wb, wb.as_of, path.name)
        await s.commit()
    assert ops.company_today.__module__ == "app.services.sankalp.ops"  # "today" is the real one again
    assert summary["entries"] == 6 and summary["calls"] == 3 and summary["so_corrections"] == 1
    assert summary["skipped"] == {"Raw Data row without an Entry ID (before Takeoff start)": 1,
                                  "Tracker row not keyed by a loaded Entry ID": 1}
    # the app's own rules give the Excel's results (the Monitor export), field by field
    assert {f: r[:2] for f, r in res.items()} == {f: (5, 0) for f in res}

    async with SessionLocal() as s:
        rows = {e.entry_code: e for e in (await s.execute(select(SankalpEntry).where(
            SankalpEntry.company_id == tenant_a["company_id"], SankalpEntry.source == "takeoff"))).scalars().all()}
        e1, e2, e3 = rows[f"{so1}-20261020-100000"], rows[f"{so1}-20261020-110000"], rows[f"{so1}-20261020-120000"]
        e5, e6, e7 = rows[f"{so1}-20261020-130000"], rows[f"{so1}-20261020-140000"], rows["UNRES-20261020-150000"]
        # a validated lead, called twice by a caller the app did not have, with its lead card and its login
        tries = (await s.execute(select(CallAttempt.outcome).where(CallAttempt.entry_id == e1.id)
                                 .order_by(CallAttempt.created_at))).scalars().all()
        assert tries == [R.RNR, R.CONNECTED] and e1.status == R.VALIDATED
        assert (e1.lead_outcome, e1.tcs_id, e1.sankalp_success, e1.customer_validated) == (R.LOGGED_IN, "TCS0009", True, True)
        pooja = await s.get(User, e1.first_caller_id)
        assert (pooja.full_name, pooja.role, pooja.employee_code, pooja.must_change_password) == ("Pooja", "caller", "CC-POOJA", True)
        card = await s.get(LeadCard, e1.id)
        assert (card.lead_id, card.loan_requirement, card.data["cibil_score"]) == ("TCS-L-1", 2500000, 750)
        # the Excel's decisions are kept, not taken again
        assert (e2.selection_status, e2.status) == (R.NC_REPEAT, None)
        assert (e5.selection_status, e5.phone) == (R.NC_NO_NUMBER, "12345")
        assert (e6.call_group, e6.selection_status) == ("none", None)
        assert e7.selection_status is None  # not decided in the Excel yet: the next daily run decides it
        unres = await s.get(User, e7.so_user_id)
        assert unres.employee_code == "UNRES" and unres.role == "sales_officer"
        # a DSA/CP contact: its new CP sub-type, the corrected SO and branch, the tracker's RAG
        assert (e3.cp_subtype_label, e3.so_user_id, e3.branch_id) == ("Mason", tenant_a["so3_id"], tenant_a["b3"])
        assert (e3.status, e3.so_action, e3.rag) == (R.DSA_GREEN, R.ACT_DSA_FOLLOWUP, "GREEN")
        assert (await s.get(FollowupTracker, e3.id)).owner == "branch"

    async with SessionLocal() as s:
        out = await T.remove(s, await s.get(Company, tenant_a["company_id"]))
        await s.commit()
    assert out["removed"] == 6
    async with SessionLocal() as s:
        left = (await s.execute(select(func.count()).select_from(SankalpEntry).where(
            SankalpEntry.company_id == tenant_a["company_id"], SankalpEntry.source == "takeoff"))).scalar_one()
        assert left == 0
        assert (await s.execute(select(User).where(User.employee_code == "CC-POOJA",
                                                   User.company_id == tenant_a["company_id"]))).scalar_one_or_none() is None
        assert (await s.get(User, tenant_a["so3_id"])) is not None  # the app's own people stay
