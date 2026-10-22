"""Create the first real company and administrator (no demo data).

    BOOTSTRAP_ADMIN_PASSWORD='...' python -m app.bootstrap \
        --company-name "Acme Ltd" --company-code acme \
        --admin-name "Jane Admin" --admin-email jane@acme.com --admin-employee-code ADM001 [--with-branches]

Publishes the form versions in database/seed/ and, with --with-branches, the branches in
database/seed/branches.json (placeholder codes: review them afterwards in the admin web).
Refuses to run if the company code or admin email already exists. The password comes from the
environment, never the command line (shell history / process list).
"""
import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Company, User
from app.security.passwords import hash_password
from app.seed import publish_seed_forms, seed_branches
from app.services.workflow import ensure_company_defaults

MIN_PASSWORD = 12


async def bootstrap(*, company_name: str, company_code: str, admin_name: str, admin_email: str,
                    admin_employee_code: str, password: str, with_branches: bool) -> dict:
    if len(password) < MIN_PASSWORD:
        raise SystemExit(f"Admin password must be at least {MIN_PASSWORD} characters.")
    email = admin_email.strip().lower()
    async with SessionLocal() as s:
        if (await s.execute(select(Company).where(Company.code == company_code))).scalar_one_or_none():
            raise SystemExit(f"Company code '{company_code}' already exists; nothing changed.")
        if (await s.execute(select(User).where(User.email == email))).scalar_one_or_none():
            raise SystemExit(f"A user with email '{email}' already exists; nothing changed.")
        co = Company(name=company_name, code=company_code)
        s.add(co)
        await s.flush()
        s.add(User(company_id=co.id, employee_code=admin_employee_code, full_name=admin_name, email=email,
                   role="admin", password_hash=await asyncio.to_thread(hash_password, password)))
        await s.flush()
        versions = await publish_seed_forms(s, co)
        branches = await seed_branches(s, co) if with_branches else []
        await ensure_company_defaults(s, co.id)
        await s.commit()
    return {"company": company_code, "admin": email, "form_versions": versions, "branches": branches}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--company-name", required=True)
    ap.add_argument("--company-code", required=True)
    ap.add_argument("--admin-name", required=True)
    ap.add_argument("--admin-email", required=True)
    ap.add_argument("--admin-employee-code", default="ADM001")
    ap.add_argument("--with-branches", action="store_true")
    a = ap.parse_args()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not password:
        sys.exit("Set BOOTSTRAP_ADMIN_PASSWORD in the environment.")
    result = asyncio.run(bootstrap(
        company_name=a.company_name, company_code=a.company_code, admin_name=a.admin_name,
        admin_email=a.admin_email, admin_employee_code=a.admin_employee_code, password=password,
        with_branches=a.with_branches))
    print(f"Created company '{result['company']}' with admin {result['admin']}.")
    print(f"Form versions published: {result['form_versions']}; branches added: {result['branches'] or 'none'}")


if __name__ == "__main__":
    main()
