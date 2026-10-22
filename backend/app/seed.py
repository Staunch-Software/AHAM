"""Development seed: python -m app.seed

Creates the demo company, branch, admin and agent if missing, adds the real branches from
database/seed/branches.json that are missing (placeholder codes), then publishes every
database/seed/field_meeting_report.v*.json form version that is newer than what the database has
(versions are immutable and monotonic, so re-running is safe and also adds new versions later).

Passwords come from SEED_ADMIN_PASSWORD / SEED_AGENT_PASSWORD env vars; if unset a random
one is generated and printed once. Not for production use.
"""
import asyncio
import json
import os
import secrets
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.forms import publish_version
from app.core.db import SessionLocal
from app.models import Branch, Company, User
from app.security.passwords import hash_password
from app.services.workflow import ensure_company_defaults

SEED_DIR = Path(__file__).resolve().parents[2] / "database" / "seed"


def _version_of(path: Path) -> int:
    return json.loads(path.read_text(encoding="utf-8"))["version"]


async def publish_seed_forms(s, company: Company) -> list[int]:
    published = []
    for path in sorted(SEED_DIR.glob("field_meeting_report.v*.json"), key=_version_of):
        schema = json.loads(path.read_text(encoding="utf-8"))
        try:
            async with s.begin_nested():
                await publish_version(s, company, schema, [None])
            published.append(schema["version"])
        except HTTPException as e:
            if e.status_code != 409:  # 409 = this version (or a newer one) already exists
                raise
    return published


async def seed_branches(s, company: Company) -> list[str]:
    """Adds any branch from branches.json that the company does not have yet (matched by code). Never edits existing ones."""
    data = json.loads((SEED_DIR / "branches.json").read_text(encoding="utf-8"))["branches"]
    have = set((await s.execute(select(Branch.code).where(Branch.company_id == company.id))).scalars().all())
    added = []
    for b in data:
        if b["code"] not in have:
            s.add(Branch(company_id=company.id, name=b["name"], code=b["code"]))
            added.append(b["name"])
    return added


async def main() -> None:
    created = None
    async with SessionLocal() as s:
        co = (await s.execute(select(Company).where(Company.code == "demo"))).scalar_one_or_none()
        if co is None:
            admin_pw = os.environ.get("SEED_ADMIN_PASSWORD") or secrets.token_urlsafe(10)
            agent_pw = os.environ.get("SEED_AGENT_PASSWORD") or secrets.token_urlsafe(10)
            co = Company(name="Demo Company", code="demo")
            s.add(co)
            await s.flush()
            br = Branch(company_id=co.id, name="Head Office", code="HO")
            s.add(br)
            await s.flush()
            s.add_all(
                [
                    User(company_id=co.id, employee_code="ADM001", full_name="Demo Admin",
                         email="admin@fieldsync-demo.com", role="admin", password_hash=hash_password(admin_pw)),
                    User(company_id=co.id, branch_id=br.id, employee_code="AGT001", full_name="Demo Agent",
                         email="agent@fieldsync-demo.com", role="agent", password_hash=hash_password(agent_pw)),
                ]
            )
            await s.flush()
            created = f"admin@fieldsync-demo.com / {admin_pw}\nagent@fieldsync-demo.com / {agent_pw}"
        published = await publish_seed_forms(s, co)
        added = await seed_branches(s, co)
        await ensure_company_defaults(s, co.id)  # starter person types + rejection reasons (only if none exist)
        await s.commit()
    print(created or "Demo company already seeded.")
    print(f"Branches added this run: {added or 'none (already present)'}")
    print(f"Form versions published this run: {published or 'none (already up to date)'}")


if __name__ == "__main__":
    asyncio.run(main())
