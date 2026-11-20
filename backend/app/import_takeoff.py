"""Load Aham's Takeoff master workbook ("Takeoff_CallCentre_Master_*.xlsx") into the app: the move from Excel.

What is loaded, from the workbook's own sheets (the facts, not the Excel's formulas):
- Raw Data: every Takeoff entry, with its Entry ID, SO, branch, category, person met, number and description. Rows
  without an Entry ID are from before Takeoff start (the old process, [Legacy]) and are not loaded; nor are entries
  the Excel marks "Discarded - old process".
- Monitor export: the Excel's decision for the entries it did not call ("Not called - ..."), so the app does not
  decide those again. Entries the Excel had not decided yet are left for the app's next daily run.
- History: every recorded try (caller, date, slot, outcome, the answers on a connected call) and the lead card.
- Earlier entries: entries of 22 Sep - 6 Oct that were called in the September file, whose tries are not in this
  workbook. Each gets one try carried over from that file, with the final status the September file gave it.
- SO corrections, Follow-up tracker (the rows keyed by an Entry ID) and Logins (the MIS login register).

The app then works out every status, RAG, action and flag with its own rules, as of the workbook's run date, and
--report writes them next to the Monitor export's values, entry by entry, to see where the two differ.

SOs, callers and CP sub-types the workbook uses are added when the app does not have them. The people get no
password they can use: HR gives one with a temporary password. Everything loaded belongs to one import batch, so
--remove takes it all out again.

  python -m app.import_takeoff PATH.xlsx [--as-of YYYY-MM-DD] [--report report.csv] [--dry-run]
  python -m app.import_takeoff --remove

It connects to DATABASE_URL like the backend. Customer names and numbers are never printed; the report has Entry
IDs and the two values only.
"""
import argparse
import asyncio
import csv
import difflib
import hashlib
import re
import secrets
import sys
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, or_, select, update

from app.core.db import SessionLocal
from app.models import (
    Branch,
    BranchAnswer,
    CallAllocation,
    CallAttempt,
    Company,
    CpSubtype,
    EntryEvent,
    FollowupTracker,
    ImportBatch,
    LeadCard,
    LoginRegisterRow,
    Photo,
    SankalpEntry,
    User,
)
from app.security.passwords import hash_password
from app.services import calendar
from app.services.periods import tz_of
from app.services.phone import clean_phone, is_valid_phone
from app.services.reference import holiday_set
from app.services.sankalp import engine as E
from app.services.sankalp import handoff, ops
from app.services.sankalp import rules as R
from app.services.sankalp.schemas import TrackerIn
from app.services.settings import load_settings
from app.services.tabular import norm_header, parse_date

KIND = "takeoff"
SOURCE = "takeoff"
OLD_PROCESS = "Discarded – old process"
# the workbook's spellings of branches the app spells differently
BRANCH_ALIASES = {"siddhipet": "Siddipet", "vilupuram": "Villupuram", "chengalpet": "Chengalpattu"}
OWNERS = {"branch": "branch", "callcentre": "call_centre", "done": "done"}
RAGS = {"green": "GREEN", "amber": "AMBER", "red": "RED", "rnr": "RNR", "na": "NA"}
EMP_CODE = re.compile(r"[A-Z]{3,6}\d{3,6}")
# the September file's final status -> the outcome of the try carried over (a connected call otherwise)
CARRIED_OUTCOME = {R.CLOSED_NO_ANSWER: R.RNR, R.DISCARDED_9: R.RNR, R.IN_RETRY: R.RNR, R.REJECTED_REFUSED: R.REFUSED,
                   R.DISCARDED_INVALID: R.INVALID_NUMBER, R.AMBER_WRONG_PERSON: R.WRONG_PERSON}
DSA_RAG_OF = {R.DSA_GREEN: "Green", R.DSA_NA: "NA", R.DSA_AMBER: "Amber", R.DSA_RED: "Red"}
SEPTEMBER = "CC-SEPFILE"
ENTRY_ID = re.compile(r"^([A-Za-z0-9]+)-(\d{8})-(\d{6})(?:-\d+)?$")


def key(v: Any) -> str:
    return re.sub(r"[^a-z0-9+]", "", str(v or "").lower())


def dashes(v: Any) -> str:
    """The Excel writes "Not called - known contact"; the app "Not called – known contact"."""
    return re.sub(r"\s+[-–—]\s+", " – ", str(v or "").strip())


def canon(v: Any, options) -> str | None:
    """The app's own spelling of a value from a fixed list, or None when it is not one of them."""
    if v in (None, ""):
        return None
    return {key(o): o for o in options}.get(key(dashes(v)))


def xl_date(v: Any) -> date | None:
    try:
        return parse_date(v)
    except ValueError:
        return None


def whole(v: Any, lo: int, hi: int) -> int | None:
    try:
        n = int(float(str(v).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def yes_no(v: Any) -> bool | None:
    k = key(v)
    return True if k.startswith("yes") else False if k.startswith("no") else None


def txt(v: Any, n: int) -> str | None:
    s = str(v).strip() if v not in (None, "") else ""
    return s[:n] or None


# ---------------------------------------------------------------- reading the workbook
def read_sheet(wb, name: str, header_row: int = 1) -> list[dict]:
    if name not in wb.sheetnames:
        return []
    rows = wb[name].iter_rows(min_row=header_row, values_only=True)
    head = [str(h).strip() if h is not None else "" for h in next(rows, [])]
    out = []
    for n, r in enumerate(rows, start=header_row + 1):
        if r and any(v not in (None, "") for v in r):
            out.append({**dict(zip(head, r)), "_row": n})
    return out


def run_date(wb) -> date | None:
    for r in wb["Control"].iter_rows(min_row=1, max_row=40, values_only=True) if "Control" in wb.sheetnames else []:
        if r and isinstance(r[0], str) and r[0].strip().lower().startswith("run date"):
            return xl_date(r[1])
    return None


@dataclass
class Workbook:
    raw: list[dict]
    monitor: dict[str, dict]
    history: list[dict]
    logins: list[dict]
    tracker: list[dict]
    corrections: list[dict]
    as_of: date | None
    earlier: dict[str, dict]


def load_workbook(path: Path) -> Workbook:
    import openpyxl  # noqa: PLC0415 - only needed here
    import warnings  # noqa: PLC0415

    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        monitor = {str(r["Entry ID"]).strip(): r for r in read_sheet(wb, "Monitor export") if r.get("Entry ID")}
        return Workbook(raw=read_sheet(wb, "Raw Data"), monitor=monitor, history=read_sheet(wb, "History"),
                        logins=[r for r in read_sheet(wb, "Logins") if any(key(k) == "tcsid" and v for k, v in r.items())],
                        tracker=[r for r in read_sheet(wb, "Follow-up tracker", header_row=4) if r.get("Key")],
                        corrections=[r for r in read_sheet(wb, "SO corrections") if r.get("Entry ID")],
                        as_of=run_date(wb),
                        earlier={str(r["Entry ID"]).strip(): r for r in read_sheet(wb, "Earlier entries") if r.get("Entry ID")})
    finally:
        wb.close()


# ---------------------------------------------------------------- the move
class Loader:
    def __init__(self, s, company: Company, actor: User, as_of: date, filename: str):
        self.s, self.co, self.actor, self.as_of, self.filename = s, company, actor, as_of, filename
        self.tz = tz_of(company.timezone)
        self.skipped: Counter = Counter()
        self.made_users: list[uuid.UUID] = []
        self.made_subtypes: list[uuid.UUID] = []
        self.dropped_answers: Counter = Counter()
        self.carried = 0

    # ---- reference data
    async def prepare(self):
        s = self.s
        self.cfg = await load_settings(s, self.co.id)
        self.branches = {key(b.name): b for b in (await s.execute(select(Branch).where(
            Branch.company_id == self.co.id))).scalars().all()}
        self.users = {u.employee_code.upper(): u for u in (await s.execute(select(User).where(
            User.company_id == self.co.id))).scalars().all()}
        self.subtypes = {key(c.label): c for c in (await s.execute(select(CpSubtype).where(
            CpSubtype.company_id == self.co.id, CpSubtype.active))).scalars().all()}
        self.batch = ImportBatch(company_id=self.co.id, kind=KIND, filename=self.filename[:255], uploaded_by=self.actor.id)
        s.add(self.batch)
        await s.flush()
        self.unusable = hash_password(secrets.token_urlsafe(24))

    def branch(self, name: Any) -> Branch | None:
        k = key(name)
        if not k or k in ("na", "none"):
            return None
        k = key(BRANCH_ALIASES.get(k, name))
        if k in self.branches:
            return self.branches[k]
        close = difflib.get_close_matches(k, list(self.branches), n=1, cutoff=0.85)
        return self.branches[close[0]] if close else None

    async def person(self, code: str, name: str, role: str, branch: Branch | None, spoke: str | None = None) -> User:
        code = code.upper()
        if code in self.users:
            return self.users[code]
        u = User(company_id=self.co.id, employee_code=code, full_name=name[:200], role=role,
                 branch_id=branch.id if branch and role == "sales_officer" else None,
                 region_id=branch.region_id if branch and role == "sales_officer" else None,
                 spoke=spoke, password_hash=self.unusable, must_change_password=True)
        self.s.add(u)
        await self.s.flush()
        self.users[code] = u
        self.made_users.append(u.id)
        return u

    async def subtype(self, label: Any) -> CpSubtype | None:
        if not label:
            return None
        k = key(label)
        if k in self.subtypes:
            return self.subtypes[k]
        # "Other Hardware Shop (electric, ...)" is "Other Hardware Shop" (the longest label it starts with, not "Other")
        starts = [ek for ek in self.subtypes if k.startswith(ek)]
        if starts:
            self.subtypes[k] = self.subtypes[max(starts, key=len)]
            return self.subtypes[k]
        c = CpSubtype(company_id=self.co.id, label=str(label).strip()[:100], sort_order=100 + len(self.made_subtypes))
        self.s.add(c)
        await self.s.flush()
        self.subtypes[k] = c
        self.made_subtypes.append(c.id)
        return c

    # ---- people
    async def roster(self, wb: Workbook):
        """The SOs of the entries and the callers of History and the tracker, where the app does not have them."""
        by_code: dict[str, list[dict]] = defaultdict(list)
        for r in wb.raw:
            if r.get("Entry ID"):
                by_code[self.emp_code(r)].append(r)
        for code, rows in by_code.items():
            if code in self.users:
                continue
            name = Counter(str(r.get("Name") or "").strip() for r in rows).most_common(1)[0][0] or code
            branch = self.branch(Counter(r.get("Branch") for r in rows).most_common(1)[0][0])
            spoke = Counter(r.get("Spoke") for r in rows).most_common(1)[0][0]
            if code == "UNRES":
                name = "Unresolved SO (Emp ID not found in the Excel)"
            await self.person(code, name, "sales_officer", branch, txt(spoke, 100))
        for r in wb.corrections:
            code = str(r.get("Correct SO Emp ID") or "").strip().upper()
            if EMP_CODE.fullmatch(code):
                await self.person(code, str(r.get("Correct SO name") or code), "sales_officer",
                                  self.branch(r.get("Correct branch (blank = keep)")))
        names = {str(r.get("Caller") or "").strip() for r in wb.history} | {str(r.get("Caller") or "").strip() for r in wb.tracker}
        self.callers = {}
        for n in sorted(x for x in names if x and key(x)):
            self.callers[key(n)] = await self.person(f"CC-{key(n).upper()[:40]}", n, "caller", None)
        self.no_name_caller = await self.person("CC-UNNAMED", "Caller (name not in the Excel)", "caller", None)
        self.september = await self.person(SEPTEMBER, "September Takeoff file (carried over)", "caller", None)
        self.september.status = "inactive"  # never on a calling list

    @staticmethod
    def emp_code(r: dict) -> str:
        """The Emp ID cell, or the code written inside it ("(... "AHFL01234")"), else the Entry ID's first part."""
        m = EMP_CODE.search(str(r.get("Emp ID") or "").upper())
        if m:
            return m.group(0)
        return str(r["Entry ID"]).split("-")[0].upper()

    # ---- entries
    async def entries(self, wb: Workbook) -> dict[str, SankalpEntry]:
        s, out = self.s, {}
        self.earlier = wb.earlier
        hist_by_entry: dict[str, list[dict]] = defaultdict(list)
        for r in wb.history:
            if r.get("Entry ID"):
                hist_by_entry[str(r["Entry ID"]).strip()].append(r)
        self.hist_by_entry = hist_by_entry
        taken = set((await s.execute(select(SankalpEntry.entry_code).where(
            SankalpEntry.company_id == self.co.id))).scalars().all())
        holidays = await holiday_set(s, self.co.id, date(2026, 1, 1))
        for r in wb.raw:
            code = str(r.get("Entry ID") or "").strip()
            if not code:
                self.skipped["Raw Data row without an Entry ID (before Takeoff start)"] += 1
                continue
            m = ENTRY_ID.match(code)
            category = canon(r.get("Category"), R.CATEGORIES.values())
            if not m or not category:
                self.skipped["Entry ID or category not readable"] += 1
                continue
            if code in taken:
                self.skipped["Entry ID already in the app"] += 1
                continue
            mon = wb.monitor.get(code, {})
            if dashes(mon.get("Master status")) == OLD_PROCESS:
                self.skipped["Discarded – old process (not built)"] += 1
                continue
            submitted = datetime.strptime(m.group(2) + m.group(3), "%Y%m%d%H%M%S").replace(tzinfo=self.tz)
            so = self.users[self.emp_code(r)]
            branch = self.branch(r.get("Branch")) or (await s.get(Branch, so.branch_id) if so.branch_id else None)
            if branch is None:
                self.skipped["Branch not in the app"] += 1
                continue
            cat = next(k for k, v in R.CATEGORIES.items() if v == category)
            sub = await self.subtype(r.get("CP Subtype")) if cat == "contact_point" else None
            raw_phone = str(r.get("Phone Number") or "").strip()
            cleaned = clean_phone(raw_phone)
            phone = cleaned if is_valid_phone(cleaned) or len(cleaned) <= 10 else ""
            d = submitted.date()
            e = SankalpEntry(
                company_id=self.co.id, entry_code=code, emp_code=m.group(1).upper(), so_user_id=so.id,
                original_so_user_id=so.id, branch_id=branch.id, spoke=txt(r.get("Spoke"), 100), category=cat,
                cp_subtype_id=sub.id if sub else None, cp_subtype_label=sub.label if sub else None,
                person_name=txt(r.get("Person Met"), 200) or "(no name in the Excel)", phone=phone,
                phone_raw=raw_phone[:50], description=str(r.get("Description") or "").strip() or "(no description)",
                submitted_at_device=submitted, entry_date=d, count_date=calendar.count_date(d, holidays),
                received_at_server=submitted, idempotency_key=f"takeoff:{code}", client_entry_id=f"takeoff:{code}",
                request_hash=hashlib.sha256(code.encode()).hexdigest(), location_status="unavailable", place_status="done",
                call_group=R.CALL_GROUP[cat], rag="PENDING" if R.CALL_GROUP[cat] != "none" else "NA", source=SOURCE,
                import_batch_id=self.batch.id)
            # the Excel's own decision for an entry it did not call; an entry it called was selected
            ms = canon(mon.get("Master status"), R.NOT_CALLED)
            if not ms:
                ms = next((canon(h.get(f"Attempt {i} outcome"), R.NOT_CALLED) for h in hist_by_entry.get(code, [])
                           for i in (1, 2, 3) if canon(h.get(f"Attempt {i} outcome"), R.NOT_CALLED)), None)
            # on a caller's sheet (a call type and a caller), whether or not a try was recorded
            called = any(key(h.get("Call type")) not in ("", "notcalled") and key(h.get("Caller"))
                         for h in hist_by_entry.get(code, []))
            if e.call_group != "none" and (ms or called or mon.get("Master status")):
                e.selection_status = ms or R.ALLOCATE
                days = sorted(x for x in (xl_date(h.get("Call date")) for h in hist_by_entry.get(code, [])) if x)
                e.selection_run_on = days[0] if days else d + timedelta(days=1)
            s.add(e)
            out[code] = e
            taken.add(code)
        await s.flush()
        for e in out.values():
            self.event(e, "import", None, e.submitted_at_device, file=self.filename)
            if e.selection_status:
                self.event(e, "selection", None, datetime.combine(e.selection_run_on, time(8), self.tz),
                           result=e.selection_status, run_date=e.selection_run_on, via="Takeoff master")
        return out

    def event(self, e: SankalpEntry, kind: str, actor: uuid.UUID | None, at: datetime, **detail):
        self.s.add(EntryEvent(entry_id=e.id, company_id=e.company_id, kind=kind, actor_id=actor, created_at=at,
                              detail={k: (v.isoformat() if isinstance(v, date) else v) for k, v in detail.items()}))

    # ---- calls and lead cards
    @staticmethod
    def outcome(v: Any) -> str | None:
        if key(v) == "rnr":
            return R.RNR
        return canon(v, R.OUTCOMES)

    def answers(self, h: dict) -> dict:
        fields = {"dsa_rag": ("DSA/CP: RAG", R.DSA_RAG), "needs_home_loan": ("DSA/CP: needs home loan himself?", ["Yes", "No"]),
                  "name_check": ("Name check", R.NAME_CHECK), "visit": ("Visit", R.VISIT),
                  "relationship": ("Relationship", R.RELATIONSHIP), "loan_need": ("Loan need", R.LOAN_NEED),
                  "timeline": ("Timeline", R.TIMELINE), "income": ("Income", R.INCOME), "documents": ("Documents", R.DOCUMENTS),
                  "next_step": ("Next step", R.NEXT_STEP), "purpose": ("Purpose", R.PURPOSE),
                  "own_contribution": ("Own contribution", R.OWN_CONTRIBUTION)}
        out: dict[str, Any] = {}
        for k, (col, options) in fields.items():
            v = h.get(col)
            if v in (None, "", "n/a"):
                continue
            c = canon(v, options)
            if c:
                out[k] = c
            else:
                self.dropped_answers[col] += 1
        if (n := txt(h.get("Name as given"), 200)) and n.lower() != "n/a":
            out["name_given"] = n
        if (d := xl_date(h.get("Next date"))):
            out["next_date"] = d.isoformat()
        if (rm := txt(h.get("Remarks"), 1000)):
            out["remarks"] = rm
        return out

    def at(self, d: date, slot: str | None, n: int) -> datetime:
        hour = 18
        if slot and re.match(r"\d{2}-\d{2}$", slot):
            hour = int(slot[:2]) + (12 if int(slot[:2]) < 9 else 0)
        return datetime.combine(d, time(hour), self.tz) + timedelta(minutes=n)

    async def calls(self, entries: dict[str, SankalpEntry]) -> int:
        s, made = self.s, 0
        for code, e in entries.items():
            rows = sorted(((xl_date(h.get("Call date")), h["_row"], h) for h in self.hist_by_entry.get(code, [])),
                          key=lambda x: (x[0] or date.max, x[1]))
            prior: list[CallAttempt] = []
            card_row = None
            for d, _, h in rows:
                tries = [(i, h.get(f"Attempt {i} slot"), self.outcome(h.get(f"Attempt {i} outcome"))) for i in (1, 2, 3)]
                tries = [t for t in tries if t[2]]
                if not tries:
                    continue
                if d is None:
                    self.skipped["Call row without a call date"] += 1
                    continue
                caller = self.callers.get(key(h.get("Caller"))) or self.no_name_caller
                connected_at = max((i for i, _, o in tries if o == R.CONNECTED), default=None)
                for i, slot, outcome in tries:
                    converted = e.call_group == "dsa_cp" and E.is_converted(prior)
                    rules_group = "lead" if converted else e.call_group
                    answers = None
                    if outcome == R.CONNECTED:
                        answers = self.answers(h) if i == connected_at else {}
                        if e.call_group == "lead":
                            answers.pop("dsa_rag", None)
                            answers.pop("needs_home_loan", None)
                        answers = E.applicable_answers(answers)
                        if converted:
                            answers.setdefault("needs_home_loan", "Yes")
                    unanswered = sum(1 for a in prior if a.outcome in R.UNANSWERED) + (outcome in R.UNANSWERED)
                    row = E.row_status(call_group=e.call_group if outcome == R.CONNECTED else rules_group, outcome=outcome,
                                       answers=answers, unanswered_after=unanswered, max_unanswered=self.cfg.max_unanswered_lead)
                    nd = (xl_date(h.get("Next date")) or xl_date(h.get("Callback due"))) if outcome == R.CALLBACK else None
                    when = self.at(d, txt(slot, 5), i)
                    a = CallAttempt(company_id=e.company_id, entry_id=e.id, caller_id=caller.id, call_date=d,
                                    slot=txt(slot, 5) or "", outcome=outcome, cycle=1, next_date=nd, answers=answers,
                                    row_status=row, created_at=when)
                    s.add(a)
                    prior.append(a)
                    made += 1
                    if e.first_caller_id is None:
                        e.first_caller_id = caller.id
                    self.event(e, "call", caller.id, when, slot=a.slot, outcome=outcome, status=row, via="Takeoff master")
                if self.card_fields(h):
                    card_row = (d, h, caller)
            if card_row:
                await self.card(e, *card_row)
            if not prior and (old := self.earlier.get(code)):
                made += self.carried_over(e, old)
        await s.flush()
        return made

    def carried_over(self, e: SankalpEntry, old: dict) -> int:
        """One try standing for the September file's calls: its final status, on its last call date."""
        status = canon(old.get("Status"), R.ALL_STATUSES)
        if not status or status in R.NOT_CALLED or e.call_group == "none":
            return 0
        outcome = CARRIED_OUTCOME.get(status, R.CONNECTED)
        d = xl_date(old.get("Last call date")) or xl_date(old.get("Last spoken")) or e.entry_date + timedelta(days=1)
        answers = ({"dsa_rag": DSA_RAG_OF[status]} if status in DSA_RAG_OF else {}) if outcome == R.CONNECTED else None
        when = self.at(d, None, 0)
        self.s.add(CallAttempt(company_id=e.company_id, entry_id=e.id, caller_id=self.september.id, call_date=d, slot="",
                               outcome=outcome, cycle=1, answers=answers, row_status=status, created_at=when))
        if e.selection_status is None:
            e.selection_status, e.selection_run_on = R.ALLOCATE, d
        self.event(e, "call", None, when, outcome=outcome, status=status, via="September Takeoff file (carried over)")
        self.carried += 1
        return 1

    def card_fields(self, h: dict) -> dict:
        vehicle = str(h.get("Vehicle (yes/no and type)") or "").strip()
        d = {"age": whole(h.get("Age"), 18, 100), "date_of_birth": xl_date(h.get("Date of birth")),
             "address": txt(h.get("Address"), 300), "city": txt(h.get("City"), 100),
             "property_pincode": (p if re.fullmatch(r"\d{6}", p := str(h.get("Property pincode") or "").strip()) else None),
             "business_pincode": (p if re.fullmatch(r"\d{6}", p := str(h.get("Business pincode") or "").strip()) else None),
             "payslip_or_itr": yes_no(h.get("Payslip or ITR available")), "job_profile": txt(h.get("Job profile"), 100),
             "individual_monthly_income": whole(h.get("Individual monthly income"), 0, 100_000_000),
             "family_monthly_income": whole(h.get("Family monthly income"), 0, 100_000_000),
             "vehicle": yes_no(vehicle), "vehicle_type": txt(re.sub(r"^(yes|no)\W*", "", vehicle, flags=re.I), 50),
             "cibil_score": whole(h.get("CIBIL score"), 300, 900),
             "bounce_last_6_months": yes_no(h.get("EMI or cheque bounce in 6 months")),
             "property_owner": txt(h.get("Property owner"), 100), "property_area": txt(h.get("Property area"), 100),
             "approved_property": txt(h.get("Approved property"), 50), "property_type": txt(h.get("Property type"), 50),
             "loan_purpose": txt(h.get("Purpose of loan"), 200)}
        d = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in d.items() if v not in (None, "") and str(v).lower() != "n/a"}
        if not d.get("vehicle"):
            d.pop("vehicle_type", None)
        extra = {"loan_requirement": whole(h.get("Loan requirement (Rs)"), 1, 1_000_000_000),
                 "lead_id": txt(h.get("Lead ID"), 50), "handling": self.branch(h.get("Handling branch"))}
        return {**d, **{k: v for k, v in extra.items() if v}} if (d or any(extra.values())) else {}

    async def card(self, e: SankalpEntry, d: date, h: dict, caller: User):
        f = self.card_fields(h)
        handling, lead_id, need = f.pop("handling", None), f.pop("lead_id", None), f.pop("loan_requirement", None)
        when = self.at(d, "06-07", 30)
        self.s.add(LeadCard(entry_id=e.id, company_id=e.company_id, handling_branch_id=handling.id if handling else None,
                            loan_requirement=need, lead_id=lead_id, lead_id_at=when if lead_id else None, data=f,
                            updated_by=caller.id, updated_at=when))
        if handling and handling.id != e.branch_id and lead_id:
            e.work_branch_id = handling.id
        if lead_id:
            self.event(e, "lead_id", caller.id, when, lead_id=lead_id, via="Takeoff master")

    # ---- corrections, tracker
    async def corrections(self, wb: Workbook, entries: dict[str, SankalpEntry]) -> int:
        done = 0
        for r in wb.corrections:
            e = entries.get(str(r["Entry ID"]).strip())
            so = self.users.get(str(r.get("Correct SO Emp ID") or "").strip().upper())
            if not e or not so:
                self.skipped["SO correction: entry or SO not found"] += 1
                continue
            if so.id == e.so_user_id:
                continue
            branch = self.branch(r.get("Correct branch (blank = keep)"))
            old = (e.so_user_id, e.branch_id)
            e.so_user_id, e.branch_id = so.id, (branch.id if branch else so.branch_id or e.branch_id)
            self.event(e, "correction.so", None, datetime.combine(self.as_of, time(9), self.tz), old_so=str(old[0]),
                       new_so=str(so.id), old_branch=str(old[1]), new_branch=str(e.branch_id), via="Takeoff master")
            done += 1
        await self.s.flush()
        return done

    async def tracker(self, wb: Workbook, entries: dict[str, SankalpEntry]) -> int:
        done = 0
        for r in wb.tracker:
            e = entries.get(str(r["Key"]).strip())
            if not e:
                self.skipped["Tracker row not keyed by a loaded Entry ID"] += 1
                continue
            caller = self.callers.get(key(r.get("Caller")))
            try:
                body = TrackerIn(owner=OWNERS.get(key(r.get("Owner"))), action_type=canon(r.get("Action type"), R.TRACKER_ACTION_TYPES),
                                 caller_id=caller.id if caller else None, followup_date=xl_date(r.get("Follow-up date")),
                                 outcome=canon(r.get("Outcome"), R.TRACKER_OUTCOMES), tcs_id=txt(r.get("TCS ID"), 50),
                                 reject_reason=canon(r.get("Reject reason"), R.TRACKER_REJECT_REASONS),
                                 rag_override=RAGS.get(key(r.get("RAG override"))), notes=txt(r.get("Notes"), 2000))
            except ValueError:
                self.skipped["Tracker row the app would refuse"] += 1
                continue
            await handoff.save_tracker(self.s, e, self.actor, body)
            done += 1
        # the tracker's date is the run date, not the day of the move
        await self.s.execute(update(FollowupTracker).where(FollowupTracker.entry_id.in_([e.id for e in entries.values()]))
                             .values(updated_at=datetime.combine(self.as_of, time(12), self.tz)))
        return done

    async def logins(self, wb: Workbook) -> dict:
        rows = [{**{norm_header(k): v for k, v in r.items() if k and k != "_row"}, "_row": r["_row"]} for r in wb.logins]
        if not rows:
            return {}
        res = await handoff.import_register(self.s, self.actor, f"{self.filename} (Logins)", rows, dry_run=False)
        return {"batch_id": res.get("batch_id"), **res["summary"]}

    async def recompute(self, entries: dict[str, SankalpEntry]):
        for e in entries.values():
            await ops.recompute(self.s, e, cfg=self.cfg, today=self.as_of, groups=False)
        for tcs in {e.tcs_id for e in entries.values() if e.tcs_id}:
            await ops.recompute_tcs_group(self.s, self.co.id, tcs, self.cfg)
        for phone in {e.phone for e in entries.values() if e.phone}:
            await ops.recompute_phone_group(self.s, self.co.id, phone)


# ---------------------------------------------------------------- the comparison with the Monitor export
def compare(wb: Workbook, entries: dict[str, SankalpEntry]) -> dict[str, tuple[int, int, Counter, list]]:
    """Per field: (agree, differ, the most common differing pairs, every difference as (Entry ID, Excel, app))."""
    fields = {
        "Status": lambda m: dashes(m.get("Master status")) or "",
        "RAG": lambda m: str(m.get("RAG") or "").strip(),
        "SO action": lambda m: str(m.get("SO action") or "").strip(),
        "CC action": lambda m: str(m.get("CC action") or "").strip(),
        "TCS ID": lambda m: str(m.get("TCS ID") or "").strip().upper(),
        "Lead outcome": lambda m: dashes(m.get("Lead outcome")) or "",
        "Counts as Sankalp success": lambda m: "Yes" if key(m.get("Counts as Sankalp success?")) in ("yes", "true", "y") else "No",
    }
    app = {
        "Status": lambda e: e.status or (e.selection_status if e.selection_status != R.ALLOCATE else "") or "",
        "RAG": lambda e: e.rag_override or e.rag,
        # the Monitor export's action column ignores the window an action stays on the lists; in the app an action
        # whose window has passed is kept as the expired action
        "SO action": lambda e: e.so_action or e.expired_action or "",
        "CC action": lambda e: e.cc_action or "",
        "TCS ID": lambda e: (e.tcs_id or "").upper(),
        "Lead outcome": lambda e: e.lead_outcome or "",
        "Counts as Sankalp success": lambda e: "Yes" if e.sankalp_success else "No",
    }
    out: dict[str, tuple[int, int, Counter, list]] = {}
    for f in fields:
        agree, pairs, lines = 0, Counter(), []
        for code, m in wb.monitor.items():
            e = entries.get(code)
            if e is None:
                continue
            x, y = fields[f](m), app[f](e)
            if key(x) == key(y):
                agree += 1
            else:
                pairs[(x, y)] += 1
                lines.append((code, x, y))
        out[f] = (agree, len(lines), pairs, lines)
    return out



async def load(s, co: Company, actor: User, wb: Workbook, as_of: date, filename: str) -> tuple[dict, dict]:
    """Everything the workbook holds, worked out as of `as_of`. Returns the batch summary and the comparison with the
    Monitor export. The caller commits (or rolls back)."""
    async def today(_s, _company_id):  # every rule works out "today" as the workbook's run date
        return as_of

    saved = {mod: mod.company_today for mod in (ops, handoff)}
    for mod in saved:
        mod.company_today = today
    try:
        ld = Loader(s, co, actor, as_of, filename)
        await ld.prepare()
        await ld.roster(wb)
        entries = await ld.entries(wb)
        n_calls = await ld.calls(entries)
        n_corr = await ld.corrections(wb, entries)
        n_tracker = await ld.tracker(wb, entries)
        logins = await ld.logins(wb)
        await ld.recompute(entries)
    finally:
        for mod, fn in saved.items():
            mod.company_today = fn
    ld.batch.rows_total, ld.batch.rows_ok, ld.batch.rows_error = len(wb.raw), len(entries), sum(ld.skipped.values())
    ld.batch.summary = {"as_of": as_of.isoformat(), "entries": len(entries), "calls": n_calls,
                        "carried_over_from_september": ld.carried, "so_corrections": n_corr,
                        "tracker_rows": n_tracker, "logins": logins, "skipped": dict(ld.skipped),
                        "users": [str(u) for u in ld.made_users], "cp_subtypes": [str(c) for c in ld.made_subtypes],
                        "answers_not_in_the_lists": dict(ld.dropped_answers)}
    await s.flush()
    return ld.batch.summary, compare(wb, entries)


def write_report(res: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Entry ID", "Field", "Excel (Monitor export)", "App"])
        for f, (_, _, _, lines) in res.items():
            w.writerows((code, f, x, y) for code, x, y in lines)


# ---------------------------------------------------------------- remove
async def remove(s, company: Company) -> dict:
    batches = (await s.execute(select(ImportBatch).where(ImportBatch.company_id == company.id,
                                                         ImportBatch.kind == KIND))).scalars().all()
    if not batches:
        return {"removed": 0}
    ids = [b.id for b in batches]
    entry_ids = select(SankalpEntry.id).where(SankalpEntry.import_batch_id.in_(ids))
    for model in (CallAllocation, CallAttempt, LeadCard, BranchAnswer, FollowupTracker, EntryEvent):
        await s.execute(delete(model).where(model.entry_id.in_(entry_ids)))
    await s.execute(update(Photo).where(Photo.entry_id.in_(entry_ids)).values(entry_id=None))
    n = (await s.execute(delete(SankalpEntry).where(SankalpEntry.import_batch_id.in_(ids)))).rowcount
    login_batches = [uuid.UUID(b.summary["logins"]["batch_id"]) for b in batches
                     if (b.summary or {}).get("logins", {}).get("batch_id")]
    if login_batches:
        await s.execute(delete(LoginRegisterRow).where(LoginRegisterRow.batch_id.in_(login_batches)))
        await s.execute(delete(ImportBatch).where(ImportBatch.id.in_(login_batches)))
    people = [uuid.UUID(u) for b in batches for u in (b.summary or {}).get("users", [])]
    subtypes = [uuid.UUID(c) for b in batches for c in (b.summary or {}).get("cp_subtypes", [])]
    await s.execute(delete(ImportBatch).where(ImportBatch.id.in_(ids)))
    kept = 0
    for uid in people:  # anyone the app has used since (an entry, a call, an upload) stays, made inactive
        try:
            async with s.begin_nested():
                await s.execute(delete(User).where(User.id == uid))
        except Exception:  # noqa: BLE001 - still referenced
            await s.execute(update(User).where(User.id == uid).values(status="inactive"))
            kept += 1
    for cid in subtypes:
        try:
            async with s.begin_nested():
                await s.execute(delete(CpSubtype).where(CpSubtype.id == cid))
        except Exception:  # noqa: BLE001
            await s.execute(update(CpSubtype).where(CpSubtype.id == cid).values(active=False))
    # entries of the app whose number a removed login matched lose that login
    await ops.recompute_many(s, company.id, or_(SankalpEntry.tcs_id.is_not(None), SankalpEntry.lead_outcome.is_not(None)))
    return {"removed": n, "people_removed": len(people) - kept, "people_kept_inactive": kept}


# ---------------------------------------------------------------- command line
async def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("path", nargs="?", type=Path, help="the Takeoff master workbook (.xlsx)")
    p.add_argument("--as-of", type=date.fromisoformat, help="work statuses out as of this day (default: the workbook's run date)")
    p.add_argument("--report", type=Path, help="write where the app and the Monitor export differ to this CSV")
    p.add_argument("--dry-run", action="store_true", help="load, compare and report, then undo everything")
    p.add_argument("--remove", action="store_true", help="take out everything an earlier load added")
    p.add_argument("--company", help="company code, when the database has more than one")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the Windows console's code page has no "→"
    async with SessionLocal() as s:
        q = select(Company)
        if a.company:
            q = q.where(Company.code == a.company)
        companies = (await s.execute(q)).scalars().all()
        if len(companies) != 1:
            print(f"Found {len(companies)} companies; pass --company with one of: {[c.code for c in companies]}")
            return 2
        co = companies[0]
        if a.remove:
            res = await remove(s, co)
            await s.commit()
            print(f"Removed {res.get('removed', 0)} loaded entries and what came with them. {res}")
            return 0
        if not a.path or not a.path.exists():
            p.error("give the workbook's path")
        if (await s.execute(select(func.count()).select_from(ImportBatch).where(
                ImportBatch.company_id == co.id, ImportBatch.kind == KIND))).scalar_one() and not a.dry_run:
            print("This database already has a Takeoff master load. Run with --remove first to load it again.")
            return 2
        print(f"Reading {a.path.name} ...", flush=True)
        wb = load_workbook(a.path)
        as_of = a.as_of or wb.as_of or date.today()
        actor = (await s.execute(select(User).where(User.company_id == co.id, User.role.in_(["master_owner", "admin"]))
                                 .order_by(User.role.desc()))).scalars().first()
        if actor is None:
            print("The company needs a Master owner or System admin account to record the move under.")
            return 2

        summary, res = await load(s, co, actor, wb, as_of, a.path.name)
        print(f"Roster: {len(summary['users'])} people added. Entries: {summary['entries']} loaded. "
              f"Calls: {summary['calls']} tries ({summary['carried_over_from_september']} carried over from the "
              f"September file). SO corrections: {summary['so_corrections']}. "
              f"Tracker rows: {summary['tracker_rows']}. Logins: {summary['logins'].get('rows', 0)} rows, "
              f"{summary['logins'].get('entries_matched', 0)} entries matched.")
        for why, n in sorted(summary["skipped"].items(), key=lambda x: -x[1]):
            print(f"  not loaded: {n} × {why}")
        for col, n in sorted(summary["answers_not_in_the_lists"].items(), key=lambda x: -x[1]):
            print(f"  answer left out (not one of the app's choices): {n} × {col}")
        print(f"\nThe app's result against the Monitor export (as of {as_of:%d %b %Y}):")
        for f, (agree, differ, pairs, _) in res.items():
            total = agree + differ
            print(f"  {f}: {agree} of {total} agree ({100 * agree / total if total else 0:.1f}%)")
            for (x, y), n in pairs.most_common(6):
                print(f"      {n} × Excel '{x or '(blank)'}' → app '{y or '(blank)'}'")
        if a.report:
            write_report(res, a.report)
            print(f"\nEvery difference, by Entry ID: {a.report}")
        if a.dry_run:
            await s.rollback()
            print("\nDry run: nothing was saved.")
        else:
            await s.commit()
            print("\nSaved. Undo with: python -m app.import_takeoff --remove")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
