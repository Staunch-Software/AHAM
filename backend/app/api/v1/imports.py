"""Uploads of reference data: the employee roster ("FOS Spoke") and daily attendance. Section 3.

Every upload can be checked first with dry_run=true: nothing is saved and the answer lists what would happen and each
row's problem. A real upload saves the good rows, reports the bad ones, and is kept in the upload history.
"""
import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_perm, require_perm
from app.core.db import get_session
from app.models import Attendance, Branch, Cluster, ImportBatch, Region, User
from app.security.passwords import hash_password, temporary_password, unusable_password_hash
from app.security.rbac import ROLES
from app.services.reference import audit
from app.services.sankalp.handoff import REGISTER_COLUMNS, import_register
from app.services.settings import load_settings
from app.services.tabular import has_column, norm_header, parse_date, pick, read_table, text

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
              "AHFL01810,Ravi Kumar,RO,Andhra Pradesh & Telangana,,Vijayawada,Benz Circle,2026-04-01,,,,\n",
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
    if not has_column(rows, ROSTER_COLUMNS["emp_code"]) or not has_column(rows, ROSTER_COLUMNS["name"]):
        raise HTTPException(422, "The roster needs at least the columns 'Emp ID' and 'Name'")
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
    seen: set[str] = set()
    created, updated, unchanged, credentials = [], [], 0, []
    for row in rows:
        n = row["_row"]
        code = (text(pick(row, ROSTER_COLUMNS["emp_code"]), 50) or "").upper()

        def err(msg: str) -> None:
            errors.append({"row": n, "emp_code": code or None, "message": msg})

        if not code:
            err("Emp ID is empty")
            continue
        if code in seen:
            err("This Emp ID appears more than once in the file")
            continue
        seen.add(code)
        name = text(pick(row, ROSTER_COLUMNS["name"]), 200)
        if not name:
            err("Name is empty")
            continue
        designation = text(pick(row, ROSTER_COLUMNS["designation"]), 50)
        role_cell = text(pick(row, ROSTER_COLUMNS["role"]), 60)
        prior = existing.get(code)
        if role_cell:
            role = role_by_label.get(norm_header(role_cell))
            if not role:
                err(f"Unknown role '{role_cell}'")
                continue
        else:
            role = cfg.designation_roles.get((designation or "").strip().upper())
            if prior and ROLES.get(prior.role) and ROLES[prior.role].level == 0:
                role = prior.role  # call-centre / HR / admin accounts are never re-roled from a designation
            if not role:
                role = prior.role if prior else None
            if not role:
                err(f"Cannot tell the role from designation '{designation or ''}': add it under Settings or fill the Role column")
                continue
        place: dict[str, Any] = {}
        try:
            for col, table in (("branch", branches), ("cluster", clusters), ("region", regions)):
                cell = text(pick(row, ROSTER_COLUMNS[col]), 200)
                if cell:
                    place[col] = table.get(norm_header(cell))
                    if not place[col]:
                        raise ValueError(f"{col.title()} '{cell}' is not in Organization")
            joining = parse_date(pick(row, ROSTER_COLUMNS["joining_date"]))
            exit_ = parse_date(pick(row, ROSTER_COLUMNS["exit_date"]))
        except ValueError as e:
            err(str(e))
            continue
        branch, cluster, region = place.get("branch"), place.get("cluster"), place.get("region")
        if branch and region and branch.region_id and branch.region_id != region.id:
            err(f"Branch {branch.name} is in region {region_names.get(branch.region_id, '?')}, not {region.name}")
            continue
        need = ROLES[role].placement
        if need and not place.get(need):
            err(f"A {ROLES[role].label} needs a {need.title()} column value")
            continue
        email = (text(pick(row, ROSTER_COLUMNS["email"]), 200) or "").lower() or None
        if email and email in emails and emails[email].employee_code.upper() != code:
            err(f"Email {email} already belongs to {emails[email].employee_code}")
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
    if not has_column(rows, ATTENDANCE_COLUMNS["emp_code"]):
        raise HTTPException(422, "Attendance needs an 'Emp ID' column")
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
            raise HTTPException(422, "Add a 'Date' and 'Status' column, or one column per date")
    errors: list[dict] = []
    marks: dict[tuple[uuid.UUID, Any], str] = {}
    for row in rows:
        code = (text(pick(row, ATTENDANCE_COLUMNS["emp_code"]), 50) or "").upper()
        uid = people.get(code)
        if not uid:
            errors.append({"row": row["_row"], "emp_code": code or None, "message": "Emp ID not on the roster"})
            continue
        if long_format:
            try:
                d = parse_date(pick(row, ATTENDANCE_COLUMNS["date"]))
            except ValueError as e:
                errors.append({"row": row["_row"], "emp_code": code, "message": str(e)})
                continue
            status = text(pick(row, ATTENDANCE_COLUMNS["code"]), 20)
            if not d or not status:
                errors.append({"row": row["_row"], "emp_code": code, "message": "Date and Status are required"})
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
    if not has_column(rows, REGISTER_COLUMNS["tcs_id"]) or not has_column(rows, REGISTER_COLUMNS["contact"]):
        raise HTTPException(422, "The register needs at least the columns 'TCS ID' and 'Customer contact'")
    result = await import_register(s, user, filename, rows, dry_run)
    if dry_run:
        await s.rollback()
        return result
    audit(s, user, "import.login_register", "import", result["batch_id"])
    await s.commit()
    return result