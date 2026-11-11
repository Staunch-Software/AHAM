"""Uploads of reference data: the employee roster ("FOS Spoke") and daily attendance. Section 3.

Every upload can be checked first with dry_run=true: nothing is saved and the answer lists what would happen and each
row's problem. A real upload saves the good rows, reports the bad ones, and is kept in the upload history.
"""
import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_perm, require_perm
from app.core.db import get_session
from app.api.v1.entries import EntryLocation, add_entry, converted_lead
from app.models import Attendance, Branch, Cluster, Company, CpSubtype, EntryEvent, ImportBatch, Region, SankalpEntry, User
from app.security.passwords import hash_password, temporary_password, unusable_password_hash
from app.security.rbac import ROLES
from app.services.periods import tz_of
from app.services.phone import clean_phone, is_valid_phone
from app.services.reference import audit
from app.services.sankalp import rules as R
from app.services.sankalp.handoff import REGISTER_COLUMNS, import_register
from app.services.settings import load_settings
from app.services.tabular import (
    column_name,
    did_you_mean,
    has_column,
    norm_header,
    parse_date,
    parse_time,
    pick,
    read_table,
    require_columns,
    row_error,
    text,
)

router = APIRouter(prefix="/imports", tags=["imports"])
MAX_FILE_BYTES = 10 * 1024 * 1024

ROSTER_COLUMNS = {
    "emp_code": ["emp id", "emp code", "employee id", "employee code", "empid", "emp no", "employee no"],
    "name": ["name", "employee name", "emp name", "full name"],
    "designation": ["designation"],
    "role": ["role", "app role"],
    "region": ["region"],
    "cluster": ["cluster"],
    "branch": ["branch", "branch name"],
    "spoke": ["spoke", "spoke name"],
    "joining_date": ["joining date", "date of joining", "doj"],
    "exit_date": ["exit date", "date of exit", "relieving date", "last working day"],
    "email": ["email", "email id", "mail id", "official email"],
    "phone": ["phone", "mobile", "mobile number", "phone number"],
}
ATTENDANCE_COLUMNS = {
    "emp_code": ROSTER_COLUMNS["emp_code"],
    "date": ["date", "attendance date", "day"],
    "code": ["status", "code", "attendance", "attendance status"],
}
TEMPLATES = {
    "roster": "Emp ID,Name,Designation,Region,Cluster,Branch,Spoke,Joining date,Exit date,Email,Phone,Role\n"
              "AHFL01810,Ravi Kumar,RO,AP & TG,,Vijayawada,Benz Circle,2026-04-01,,,,\n",
    "attendance": "Emp ID,Date,Status\nAHFL01810,2026-10-15,P\n",
    "login_register": "TCS ID,Customer contact,Login date,Product,Final status,Source,Emp code\n"
                      "TCS123456,9876543210 / 9123456780,2026-10-20,Home Loan,Logged in,Sankalp,AHFL01810\n",
}


async def _read_upload(file: UploadFile) -> tuple[str, list[dict[str, Any]]]:
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "File too large (10 MB max)")
    return file.filename or "upload", read_table(file.filename or "", data)


def _lookup(rows, key=lambda o: o.name) -> dict[str, Any]:
    """Name or code (case-insensitive) -> object."""
    out: dict[str, Any] = {}
    for o in rows:
        out[norm_header(key(o))] = o
        out[norm_header(o.code)] = o
    return out


@router.get("/templates/{kind}", response_class=PlainTextResponse)
async def template(kind: str, user: User = Depends(require_any_perm("reference.import", "login_register.upload"))):
    if kind not in TEMPLATES:
        raise HTTPException(404, "Unknown template")
    return PlainTextResponse(TEMPLATES[kind], media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{kind}_template.csv"'})


@router.get("")
async def history(kind: str | None = None, user: User = Depends(require_any_perm("reference.import", "login_register.upload")),
                  s: AsyncSession = Depends(get_session)):
    q = select(ImportBatch, User.full_name).join(User, User.id == ImportBatch.uploaded_by).where(
        ImportBatch.company_id == user.company_id).order_by(ImportBatch.created_at.desc()).limit(100)
    if kind:
        q = q.where(ImportBatch.kind == kind)
    return [{"id": str(b.id), "kind": b.kind, "filename": b.filename, "uploaded_by": name, "created_at": b.created_at,
             "rows_total": b.rows_total, "rows_ok": b.rows_ok, "rows_error": b.rows_error, "summary": b.summary,
             "errors": (b.errors or [])[:200]} for b, name in (await s.execute(q)).all()]


def _batch(user: User, kind: str, filename: str, total: int, errors: list, summary: dict) -> ImportBatch:
    return ImportBatch(company_id=user.company_id, kind=kind, filename=filename[:255], uploaded_by=user.id,
                       rows_total=total, rows_error=len({e["row"] for e in errors}),
                       rows_ok=total - len({e["row"] for e in errors}), summary=summary, errors=errors[:1000])


# ---------------------------------------------------------------- roster
@router.post("/roster")
async def import_roster(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    issue_passwords: bool = Form(False),
    user: User = Depends(require_perm("reference.import")),
    s: AsyncSession = Depends(get_session),
):
    """Adds or updates employees by Emp ID. The role comes from the Role column, else from the designation
    (Settings > designation roles: RO / RM / ABM are Sales Officers, BM is Branch Manager, ...).

    New people get no usable password; with issue_passwords=true each one gets a temporary password, returned
    once in this answer, which they must replace at first sign-in."""
    filename, rows = await _read_upload(file)
    require_columns(rows, {"Emp ID": ROSTER_COLUMNS["emp_code"], "Name": ROSTER_COLUMNS["name"]}, "roster")
    col = {k: column_name(rows, a) for k, a in ROSTER_COLUMNS.items()}
    cfg = await load_settings(s, user.company_id)
    cid = user.company_id
    branches = _lookup((await s.execute(select(Branch).where(Branch.company_id == cid))).scalars().all())
    clusters = _lookup((await s.execute(select(Cluster).where(Cluster.company_id == cid))).scalars().all())
    regions = _lookup((await s.execute(select(Region).where(Region.company_id == cid))).scalars().all())
    region_names = {r.id: r.name for r in regions.values()}
    existing = {u.employee_code.upper(): u for u in (await s.execute(select(User).where(User.company_id == cid))).scalars().all()}
    emails = {u.email: u for u in (await s.execute(select(User).where(User.email.is_not(None)))).scalars().all()}
    role_by_label = {norm_header(r.label): k for k, r in ROLES.items()} | {norm_header(k): k for k in ROLES}

    errors: list[dict] = []
    seen: dict[str, int] = {}
    created, updated, unchanged, credentials = [], [], 0, []
    for row in rows:
        n = row["_row"]
        code = (text(pick(row, ROSTER_COLUMNS["emp_code"]), 50) or "").upper()

        def err(key: str | None, value: Any, msg: str) -> None:
            errors.append(row_error(n, col[key] if key else None, value, msg, emp_code=code or None))

        if not code:
            err("emp_code", "", "Emp ID is empty. Every row needs the person's Emp ID, for example AHFL01810")
            continue
        if code in seen:
            err("emp_code", code, f"This Emp ID is already on row {seen[code]}. Keep one row per person")
            continue
        seen[code] = n
        name = text(pick(row, ROSTER_COLUMNS["name"]), 200)
        if not name:
            err("name", "", "Name is empty. Write the person's full name")
            continue
        designation = text(pick(row, ROSTER_COLUMNS["designation"]), 50)
        role_cell = text(pick(row, ROSTER_COLUMNS["role"]), 60)
        prior = existing.get(code)
        if role_cell:
            role = role_by_label.get(norm_header(role_cell))
            if not role:
                err("role", role_cell, "Unknown role. Use one of: " + ", ".join(r.label for r in ROLES.values())
                    + "; or leave the Role column empty to take the role from the designation")
                continue
        else:
            role = cfg.designation_roles.get((designation or "").strip().upper())
            if prior and ROLES.get(prior.role) and ROLES[prior.role].level == 0:
                role = prior.role  # call-centre / HR / admin accounts are never re-roled from a designation
            if not role:
                role = prior.role if prior else None
            if not role:
                err("designation", designation or "", "Cannot tell the role from this designation. Use one of "
                    + ", ".join(sorted(cfg.designation_roles)) + " (Settings: designation roles), or fill the Role column")
                continue
        place: dict[str, Any] = {}
        bad = False
        for key, table in (("branch", branches), ("cluster", clusters), ("region", regions)):
            cell = text(pick(row, ROSTER_COLUMNS[key]), 200)
            if cell:
                place[key] = table.get(norm_header(cell))
                if not place[key]:
                    names = sorted({o.name for o in table.values()})
                    err(key, cell, f"There is no {key} with this name or code under Organization."
                        f"{did_you_mean(cell, names)} Write it exactly as shown there")
                    bad = True
        dates: dict[str, Any] = {}
        for key in ("joining_date", "exit_date"):
            try:
                dates[key] = parse_date(pick(row, ROSTER_COLUMNS[key]))
            except ValueError as e:
                err(key, pick(row, ROSTER_COLUMNS[key]), str(e))
                bad = True
        if bad:
            continue
        joining, exit_ = dates["joining_date"], dates["exit_date"]
        branch, cluster, region = place.get("branch"), place.get("cluster"), place.get("region")
        if branch and region and branch.region_id and branch.region_id != region.id:
            err("region", region.name, f"Branch {branch.name} is in region {region_names.get(branch.region_id, '?')}, "
                f"not {region.name}. Correct the Region or the Branch column")
            continue
        need = ROLES[role].placement
        if need and not place.get(need):
            err(need, "", f"A {ROLES[role].label} must be placed in a {need}: fill the {col[need]} column")
            continue
        email = (text(pick(row, ROSTER_COLUMNS["email"]), 200) or "").lower() or None
        if email and email in emails and emails[email].employee_code.upper() != code:
            err("email", email, f"This email already belongs to {emails[email].employee_code}. "
                "Each person needs their own email, or leave it empty")
            continue
        values = {
            "full_name": name, "designation": designation, "role": role,
            "branch_id": branch.id if branch else None,
            "cluster_id": cluster.id if cluster else None,
            "region_id": region.id if region and need == "region" else None,
            "spoke": text(pick(row, ROSTER_COLUMNS["spoke"]), 100),
            "joining_date": joining, "exit_date": exit_,
        }
        if email:
            values["email"] = email
        phone = text(pick(row, ROSTER_COLUMNS["phone"]), 30)
        if phone:
            values["phone"] = phone
        if prior:
            changes = {k: v for k, v in values.items() if getattr(prior, k) != v}
            if changes:
                for k, v in changes.items():
                    setattr(prior, k, v)
                updated.append({"emp_code": code, "fields": sorted(changes)})
            else:
                unchanged += 1
        else:
            u = User(company_id=cid, employee_code=code, must_change_password=True, status="active", **values)
            if issue_passwords and not dry_run:
                pw = temporary_password()
                u.password_hash = await asyncio.to_thread(hash_password, pw)
                credentials.append({"emp_code": code, "name": name, "temporary_password": pw})
            else:
                u.password_hash = unusable_password_hash()
            s.add(u)
            existing[code] = u
            if email:
                emails[email] = u
            created.append({"emp_code": code, "name": name, "role": role})
    summary = {"created": len(created), "updated": len(updated), "unchanged": unchanged, "errors": len(errors)}
    result = {"dry_run": dry_run, "summary": summary, "created": created[:500], "updated": updated[:500],
              "errors": errors[:1000]}
    if dry_run:
        await s.rollback()
        return result
    batch = _batch(user, "roster", filename, len(rows), errors, summary)
    s.add(batch)
    audit(s, user, "import.roster", "import", batch.id)
    await s.commit()
    return {**result, "batch_id": str(batch.id), "credentials": credentials}


# ---------------------------------------------------------------- attendance
@router.post("/attendance")
async def import_attendance(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    user: User = Depends(require_perm("reference.import")),
    s: AsyncSession = Depends(get_session),
):
    """Long format (Emp ID, Date, Status: one row per person per day) or wide format (Emp ID, then one column per
    date). A later upload for the same person and day replaces the earlier code."""
    filename, rows = await _read_upload(file)
    require_columns(rows, {"Emp ID": ATTENDANCE_COLUMNS["emp_code"]}, "attendance file")
    col = {k: column_name(rows, a) for k, a in ATTENDANCE_COLUMNS.items()}
    people = {code.upper(): uid for uid, code in (await s.execute(
        select(User.id, User.employee_code).where(User.company_id == user.company_id))).all()}
    long_format = has_column(rows, ATTENDANCE_COLUMNS["date"])
    date_columns: dict[str, Any] = {}
    if not long_format:
        for h in rows[0]:
            if h == "_row":
                continue
            try:  # headers are normalised ("15/10/2026" -> "15 10 2026"; an Excel date -> "2026 10 15 00 00 00")
                d = parse_date("-".join(h.split()[:3]))
            except ValueError:
                continue
            if d:
                date_columns[h] = d
        if not date_columns:
            raise HTTPException(422, "The attendance file needs either the columns 'Date' and 'Status' (one row per "
                                     "person per day), or one column per date with the date as its heading. Columns "
                                     "found: " + ", ".join(f"'{h}'" for h in getattr(rows, "headers", {}).values()))
    errors: list[dict] = []
    marks: dict[tuple[uuid.UUID, Any], str] = {}
    for row in rows:
        code = (text(pick(row, ATTENDANCE_COLUMNS["emp_code"]), 50) or "").upper()
        uid = people.get(code)
        if not uid:
            msg = ("This Emp ID is not on the employee roster. Upload the roster first, or correct the Emp ID" if code
                   else "Emp ID is empty. Every row needs the person's Emp ID")
            errors.append(row_error(row["_row"], col["emp_code"], code, msg, emp_code=code or None))
            continue
        if long_format:
            try:
                d = parse_date(pick(row, ATTENDANCE_COLUMNS["date"]))
            except ValueError as e:
                errors.append(row_error(row["_row"], col["date"], pick(row, ATTENDANCE_COLUMNS["date"]), str(e), emp_code=code))
                continue
            status = text(pick(row, ATTENDANCE_COLUMNS["code"]), 20)
            if not d or not status:
                key = "date" if not d else "code"
                errors.append(row_error(row["_row"], col[key], "", f"{col[key]} is empty. Every row needs a date and an "
                                        "attendance code such as P, P(MS), P(R) or AB", emp_code=code))
                continue
            marks[(uid, d)] = status.upper().replace(" ", "")
        else:
            for h, d in date_columns.items():
                status = text(row.get(h), 20)
                if status:
                    marks[(uid, d)] = status.upper().replace(" ", "")
    summary = {"marks": len(marks), "people": len({k[0] for k in marks}), "errors": len(errors),
               "from": min((k[1] for k in marks), default=None), "to": max((k[1] for k in marks), default=None)}
    if dry_run:
        return {"dry_run": True, "summary": summary, "errors": errors[:1000]}
    if marks:
        values = [{"user_id": uid, "day": d, "company_id": user.company_id, "code": c} for (uid, d), c in marks.items()]
        for i in range(0, len(values), 1000):
            stmt = pg_insert(Attendance).values(values[i:i + 1000])
            await s.execute(stmt.on_conflict_do_update(index_elements=["user_id", "day"], set_={"code": stmt.excluded.code}))
    batch = _batch(user, "attendance", filename, len(rows), errors, {**summary, "from": str(summary["from"]), "to": str(summary["to"])})
    s.add(batch)
    audit(s, user, "import.attendance", "import", batch.id)
    await s.commit()
    return {"dry_run": False, "summary": summary, "errors": errors[:1000], "batch_id": str(batch.id)}


# ---------------------------------------------------------------- login register (section 11)
@router.post("/login-register")
async def import_login_register(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    user: User = Depends(require_perm("login_register.upload")),
    s: AsyncSession = Depends(get_session),
):
    """The MIS login register: TCS ID, customer contact (up to 3 numbers), login date, product, final status, source,
    Emp code. Logins are matched to entries on every number of the contact cell; the lead ID never counts as a login."""
    filename, rows = await _read_upload(file)
    require_columns(rows, {"TCS ID": REGISTER_COLUMNS["tcs_id"], "Customer contact": REGISTER_COLUMNS["contact"]},
                    "login register")
    result = await import_register(s, user, filename, rows, dry_run)
    if dry_run:
        await s.rollback()
        return result
    audit(s, user, "import.login_register", "import", result["batch_id"])
    await s.commit()
    return result

# ---------------------------------------------------------------- bulk entries (client feedback, Nov 2026)
ENTRY_COLUMNS = {
    "emp_code": ROSTER_COLUMNS["emp_code"],
    "date": ["date met", "date", "meeting date", "entry date", "date of meeting"],
    "time": ["time met", "time", "meeting time", "time of meeting"],
    "category": ["category", "who was met", "type"],
    "cp_subtype": ["cp sub type", "cp subtype", "sub type", "contact point type"],
    "name": ["name of person met", "person met", "name", "customer name", "person name"],
    "phone": ["mobile number", "mobile", "phone", "mobile whatsapp number", "whatsapp number", "customer mobile"],
    "description": ["description", "remarks", "notes", "meeting notes"],
    "keka": ["keka photo time", "keka time"],
}
TEMPLATES["entries"] = ("Emp ID,Date met,Time met,Category,CP sub-type,Name of person met,Mobile number,Description,Keka photo time\n"
                        "AHFL01810,2026-11-05,10:30,Lead,,Ravi Teja,9876543210,Wants to buy a flat in Benz Circle,10:28\n"
                        "AHFL01810,2026-11-05,11:15,Contact Point,Other Hardware Shop,Sri Sai Hardware,9123456780,"
                        "Hardware shop near the bus stand,\n")


@router.post("/entries")
async def import_entries(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    user: User = Depends(require_perm("reference.import")),
    s: AsyncSession = Depends(get_session),
):
    """Entries in bulk, for meetings the SOs could not enter on the phone. Each row passes the same checks as an
    entry made on the phone (Sales Officer on the roster, category, mobile number, not already a converted lead);
    its Entry ID and dates come from the date and time met. No GPS. A row already uploaded is not added again, so
    the same file can be uploaded twice safely. The entries then go through the daily selection like any other."""
    filename, rows = await _read_upload(file)
    require_columns(rows, {"Emp ID": ENTRY_COLUMNS["emp_code"], "Date met": ENTRY_COLUMNS["date"],
                           "Time met": ENTRY_COLUMNS["time"], "Category": ENTRY_COLUMNS["category"],
                           "Name of person met": ENTRY_COLUMNS["name"], "Mobile number": ENTRY_COLUMNS["phone"],
                           "Description": ENTRY_COLUMNS["description"]}, "entries file")
    col = {k: column_name(rows, a) for k, a in ENTRY_COLUMNS.items()}
    cid = user.company_id
    company = await s.get(Company, cid)
    tz = tz_of(company.timezone)
    now = datetime.now(timezone.utc)
    people = {u.employee_code.upper(): u for u in (await s.execute(select(User).where(User.company_id == cid))).scalars().all()}
    categories = {norm_header(k): k for k in R.CATEGORIES} | {norm_header(v): k for k, v in R.CATEGORIES.items()} | {
        "dsa": "dsa_connector", "connector": "dsa_connector", "dsa connector": "dsa_connector", "cp": "contact_point"}
    subtypes = {norm_header(c.label): c for c in (await s.execute(select(CpSubtype).where(CpSubtype.company_id == cid))).scalars().all()}

    errors: list[dict] = []
    ready: list[dict] = []
    seen: dict[tuple, int] = {}
    already = 0
    for row in rows:
        n = row["_row"]
        code = (text(pick(row, ENTRY_COLUMNS["emp_code"]), 50) or "").upper()
        bad: list[dict] = []

        def err(key: str, value: Any, msg: str) -> None:
            bad.append(row_error(n, col[key], value, msg, emp_code=code or None))

        so = people.get(code)
        if not code:
            err("emp_code", "", "Emp ID is empty. Write the Emp ID of the Sales Officer who met the person")
        elif not so:
            err("emp_code", code, "This Emp ID is not on the employee roster. Upload the roster first, or correct the Emp ID")
        elif so.role != "sales_officer":
            err("emp_code", code, f"{so.full_name} is a {ROLES[so.role].label}, not a Sales Officer. Only Sales Officers make entries")
        elif not so.branch_id:
            err("emp_code", code, f"{so.full_name} has no branch on the roster. Fix the roster first")
        met_day = met_time = None
        try:
            met_day = parse_date(pick(row, ENTRY_COLUMNS["date"]))
            if not met_day:
                err("date", "", "Date met is empty")
        except ValueError as e:
            err("date", pick(row, ENTRY_COLUMNS["date"]), str(e))
        try:
            met_time = parse_time(pick(row, ENTRY_COLUMNS["time"]))
            if not met_time:
                err("time", "", "Time met is empty. The Entry ID is made from the date and time, so both are needed")
        except ValueError as e:
            err("time", pick(row, ENTRY_COLUMNS["time"]), str(e))
        met = datetime.combine(met_day, met_time, tzinfo=tz) if met_day and met_time else None
        if met and met > now + timedelta(minutes=5):
            err("date", pick(row, ENTRY_COLUMNS["date"]), "This date and time is in the future")
        if met and so and so.role == "sales_officer":
            if so.joining_date and met_day < so.joining_date:
                err("date", pick(row, ENTRY_COLUMNS["date"]), f"{so.full_name} joined on {so.joining_date:%d-%m-%Y}, after this date")
            if so.exit_date and met_day > so.exit_date:
                err("date", pick(row, ENTRY_COLUMNS["date"]), f"{so.full_name} left on {so.exit_date:%d-%m-%Y}, before this date")
        cat_cell = text(pick(row, ENTRY_COLUMNS["category"]), 60)
        category = categories.get(norm_header(cat_cell)) if cat_cell else None
        if not category:
            err("category", cat_cell or "", "Unknown category. Use one of: " + ", ".join(R.CATEGORIES.values()))
        subtype = None
        sub_cell = text(pick(row, ENTRY_COLUMNS["cp_subtype"]), 100)
        if category == "contact_point":
            subtype = subtypes.get(norm_header(sub_cell)) if sub_cell else None
            if not subtype:
                labels = sorted(c.label for c in subtypes.values())
                err("cp_subtype", sub_cell or "", "A Contact Point needs its CP sub-type." + (did_you_mean(sub_cell, labels) if sub_cell else "")
                    + " Use one of: " + ", ".join(labels))
        name = text(pick(row, ENTRY_COLUMNS["name"]), 200)
        if not name:
            err("name", "", "Name of the person met is empty")
        raw_phone = text(pick(row, ENTRY_COLUMNS["phone"]), 50) or ""
        phone = clean_phone(raw_phone)
        if not is_valid_phone(phone):
            err("phone", raw_phone, "Not a valid mobile number: 10 digits starting with 6, 7, 8 or 9 (+91 or 0 in front is fine)")
        description = text(pick(row, ENTRY_COLUMNS["description"]), 2000)
        if not description:
            err("description", "", "Description is empty. Write a short note of the meeting")
        try:
            keka = parse_time(pick(row, ENTRY_COLUMNS["keka"]))
        except ValueError as e:
            err("keka", pick(row, ENTRY_COLUMNS["keka"]), str(e))
            keka = None
        if bad:
            errors.extend(bad)
            continue
        key = (code, met.isoformat(), phone)
        if key in seen:
            errors.append(row_error(n, col["phone"], raw_phone, f"The same as row {seen[key]} (same Sales Officer, date, time "
                                    "and mobile number). Keep one row per meeting", emp_code=code))
            continue
        seen[key] = n
        idem = "import-" + hashlib.sha256("|".join([str(cid), *key]).encode()).hexdigest()[:40]
        if (await s.execute(select(SankalpEntry.id).where(SankalpEntry.company_id == cid,
                                                          SankalpEntry.idempotency_key == idem))).first():
            already += 1  # uploaded before: not added twice
            continue
        if lead := await converted_lead(s, cid, phone):
            errors.append(row_error(n, col["phone"], raw_phone, lead["message"], emp_code=code))
            continue
        ready.append({"so": so, "category": category, "subtype": subtype, "name": name, "phone": phone, "raw": raw_phone,
                      "description": description, "keka": keka, "met": met, "idem": idem, "row": n})
    summary = {"rows": len(rows), "new_entries": len(ready), "already_uploaded": already, "errors": len({e["row"] for e in errors})}
    if dry_run:
        return {"dry_run": True, "summary": summary, "errors": errors[:1000]}
    batch = _batch(user, "entries", filename, len(rows), errors, summary)
    s.add(batch)
    await s.flush()
    created = []
    for r in ready:
        e = await add_entry(s, r["so"], category=r["category"], subtype=r["subtype"], name=r["name"], phone=r["phone"],
                            phone_raw=r["raw"], description=r["description"], keka_photo_time=r["keka"], submitted_at=r["met"],
                            tz_offset=int(r["met"].utcoffset().total_seconds() // 60), received=now, idempotency_key=r["idem"],
                            client_entry_id=f"{batch.id}:{r['row']}", req_hash=r["idem"], location=EntryLocation(),
                            source="import", import_batch_id=batch.id)
        e.location_status = "bulk_upload"
        await s.flush()
        s.add(EntryEvent(entry_id=e.id, company_id=cid, kind="created", actor_id=user.id,
                         detail={"entry_code": e.entry_code, "bulk_upload": filename, "row": r["row"]}))
        created.append({"entry_code": e.entry_code, "emp_code": e.emp_code, "person_name": e.person_name})
    audit(s, user, "import.entries", "import", batch.id, details={"new_entries": len(created)})
    await s.commit()
    return {"dry_run": False, "summary": summary, "errors": errors[:1000], "created": created[:500], "batch_id": str(batch.id)}
