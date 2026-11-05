"""Create the first real company and system administrator (no demo data).

    BOOTSTRAP_ADMIN_PASSWORD='...' python -m app.bootstrap \
        --company-name "AHAM Housing Finance" --company-code aham \
        --admin-name "Jane Admin" --admin-email jane@ahamhfc.com --admin-employee-code ADM001 [--with-org]

With --with-org, also adds the regions and branches of database/seed/aham_org.json (placeholder branch codes: review
them afterwards in the HR & Admin portal). Everyone else comes in through the roster upload.
Refuses to run if the company code or admin email already exists. The password comes from the environment, never
the command line (shell history / process list).
"""
import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Company, User
from app.security.passwords import hash_password
from app.seed import seed_org
from app.services.reference import ensure_company_defaults

MIN_PASSWORD = 12


async def bootstrap(*, company_name: str, company_code: str, admin_name: str, admin_email: str,
                    admin_employee_code: str, password: str, with_org: bool) -> dict:
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
        s.add(User(company_id=co.id, employee_code=admin_employee_code.upper(), full_name=admin_name, email=email,
                   role="admin", designation="Admin", password_hash=await asyncio.to_thread(hash_password, password)))
        await s.flush()
        org = await seed_org(s, co) if with_org else []
        await ensure_company_defaults(s, co.id)
        await s.commit()
    return {"company": company_code, "admin": email, "org": org}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--company-name", required=True)
    ap.add_argument("--company-code", required=True)
    ap.add_argument("--admin-name", required=True)
    ap.add_argument("--admin-email", required=True)
    ap.add_argument("--admin-employee-code", default="ADM001")
    ap.add_argument("--with-org", action="store_true")
    a = ap.parse_args()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not password:
        sys.exit("Set BOOTSTRAP_ADMIN_PASSWORD in the environment.")
    result = asyncio.run(bootstrap(
        company_name=a.company_name, company_code=a.company_code, admin_name=a.admin_name,
        admin_email=a.admin_email, admin_employee_code=a.admin_employee_code, password=password,
        with_org=a.with_org))
    print(f"Created company '{result['company']}' with admin {result['admin']} (HR & Admin portal).")
    print(f"Regions and branches added: {len(result['org'])}")


if __name__ == "__main__":
    main()
