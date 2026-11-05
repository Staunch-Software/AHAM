"""Development seed: python -m app.seed

Creates the AHAM demo company if missing: the 7 regions and their branches from database/seed/aham_org.json
(placeholder branch codes), one demo cluster ("AP Coastal": Vijayawada, Guntur, Nellore), the starter CP sub-types,
default settings, and one demo account per role. Re-running adds missing regions/branches only; it never edits rows.

All demo accounts share one password: SEED_PASSWORD from the environment, or a random one printed once.
Sign in with the Emp ID (or the email) at the portal of the role. Not for production use.
"""
import asyncio
import json
import os
import secrets
from pathlib import Path

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Branch, Cluster, Company, Region, User
from app.security.passwords import hash_password
from app.services.reference import ensure_company_defaults

SEED_DIR = Path(__file__).resolve().parents[2] / "database" / "seed"
COMPANY_CODE = "aham"

# (emp code, name, role, designation, placement kind, placement name)
DEMO_USERS = [
    ("AHFL90001", "Ravi Kumar", "sales_officer", "RO", "branch", "Vijayawada"),
    ("AHFL90002", "Lakshmi Devi", "sales_officer", "RM", "branch", "Guntur"),
    ("AHFL90011", "Suresh Reddy", "branch_manager", "BM", "branch", "Vijayawada"),
    ("AHFL90021", "Anil Varma", "cluster_manager", "RTM", "cluster", "AP Coastal"),
    ("AHFL90031", "Prakash Rao", "region_manager", "RBH", "region", "AP & TG"),
    ("AHFL90041", "Meena Iyer", "product_manager", "Product Manager", None, None),
    ("AHFL90051", "Karthik Raman", "business_manager", "Business Manager", None, None),
    ("AHFL90061", "Divya S", "caller", "Caller", None, None),
    ("AHFL90062", "Farhan Ali", "caller", "Caller", None, None),
    ("AHFL90071", "Geetha M", "master_owner", "Call-centre lead", None, None),
    ("AHFL90081", "Hari Prasad", "sankalp_monitor", "HR", None, None),
    ("AHFL90091", "Indira N", "mis", "MIS", None, None),
    ("AHFL90099", "Demo Admin", "admin", "Admin", None, None),
]


async def seed_org(s, company: Company) -> list[str]:
    """Adds regions/branches from aham_org.json that the company does not have yet (matched by code)."""
    data = json.loads((SEED_DIR / "aham_org.json").read_text(encoding="utf-8"))
    regions = {r.code: r for r in (await s.execute(select(Region).where(Region.company_id == company.id))).scalars()}
    have = set((await s.execute(select(Branch.code).where(Branch.company_id == company.id))).scalars())
    added = []
    for reg in data["regions"]:
        region = regions.get(reg["code"])
        if region is None:
            region = Region(company_id=company.id, code=reg["code"], name=reg["name"])
            s.add(region)
            await s.flush()
            added.append(f"region {reg['name']}")
        for name, code in reg["branches"]:
            if code not in have:
                s.add(Branch(company_id=company.id, region_id=region.id, name=name, code=code))
                added.append(name)
    await s.flush()
    return added


async def main() -> None:
    async with SessionLocal() as s:
        co = (await s.execute(select(Company).where(Company.code == COMPANY_CODE))).scalar_one_or_none()
        fresh = co is None
        if fresh:
            co = Company(name="AHAM Housing Finance", code=COMPANY_CODE, timezone="Asia/Kolkata")
            s.add(co)
            await s.flush()
        added = await seed_org(s, co)
        await ensure_company_defaults(s, co.id)
        password = None
        if fresh:
            region = (await s.execute(select(Region).where(Region.company_id == co.id, Region.code == "APTG"))).scalar_one()
            cluster = Cluster(company_id=co.id, region_id=region.id, name="AP Coastal", code="APC")
            s.add(cluster)
            await s.flush()
            branches = {b.name: b for b in (await s.execute(select(Branch).where(Branch.company_id == co.id))).scalars()}
            for name in ("Vijayawada", "Guntur", "Nellore"):
                branches[name].cluster_id = cluster.id
            password = os.environ.get("SEED_PASSWORD") or secrets.token_urlsafe(9)
            pw_hash = hash_password(password)
            places = {"branch": branches, "cluster": {cluster.name: cluster}, "region": {region.name: region}}
            for code, name, role, designation, kind, place in DEMO_USERS:
                u = User(company_id=co.id, employee_code=code, full_name=name, role=role, designation=designation,
                         email=f"{code.lower()}@aham-demo.in", password_hash=pw_hash)
                if kind:
                    setattr(u, f"{kind}_id", places[kind][place].id)
                s.add(u)
        await s.commit()
    if password:
        print("AHAM demo company created. Every demo account uses this password (dev only):", password)
        for code, name, role, *_ in DEMO_USERS:
            print(f"  {code}  {role:<17} {name}")
    else:
        print("AHAM demo company already seeded.")
    print(f"Regions/branches added this run: {added or 'none (already present)'}")


if __name__ == "__main__":
    asyncio.run(main())
