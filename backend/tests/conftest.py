import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
import pytest_asyncio

TEST_DB = os.environ.get("TEST_DB_NAME", "fieldsync_test")  # a second name lets two test runs work side by side
BASE_URL = os.environ.get(
    "TEST_DATABASE_SERVER", "postgresql+asyncpg://fieldsync:fieldsync_dev@localhost:5433"
)
os.environ["DATABASE_URL"] = f"{BASE_URL}/{TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret-at-least-32-bytes-long!!"
os.environ["GEOCODER"] = "none"  # no network lookups in tests (geocoding is tested with fakes)
os.environ["STORAGE_ROOT"] = str(Path(__file__).parent / ".storage")
PASSWORD = "password123"

import asyncpg  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    import asyncio

    async def recreate():
        dsn = BASE_URL.replace("+asyncpg", "") + "/postgres"
        conn = await asyncpg.connect(dsn)
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
        await conn.close()

    asyncio.run(recreate())
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest_asyncio.fixture(scope="session")
async def client():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# Who is placed where in every test company:
#   region R1: cluster C1 = {B1}, plus B2 (no cluster, no BM);  region R2: B3
# (key, role, placement kind, placement key)
PEOPLE = [
    ("so1", "sales_officer", "branch", "B1"), ("so2", "sales_officer", "branch", "B2"),
    ("so3", "sales_officer", "branch", "B3"),
    ("bm1", "branch_manager", "branch", "B1"), ("bm3", "branch_manager", "branch", "B3"),
    ("cm1", "cluster_manager", "cluster", "C1"), ("rm1", "region_manager", "region", "R1"),
    ("pm", "product_manager", None, None), ("bizm", "business_manager", None, None),
    ("caller1", "caller", None, None), ("caller2", "caller", None, None), ("master", "master_owner", None, None),
    ("monitor", "sankalp_monitor", None, None), ("mis", "mis", None, None), ("admin", "admin", None, None),
]


async def make_company() -> dict:
    """A fresh company with the PEOPLE above. Returns ids, Emp IDs ("<key>_code") and emails ("<key>_email")."""
    from app.core.db import SessionLocal
    from app.models import Branch, Cluster, Company, Region, User
    from app.security.passwords import hash_password
    from app.services.reference import ensure_company_defaults

    tag = uuid.uuid4().hex[:6].upper()
    pw = hash_password(PASSWORD)
    async with SessionLocal() as s:
        co = Company(name=f"Co {tag}", code=f"co-{tag.lower()}")
        s.add(co)
        await s.flush()
        r1, r2 = Region(company_id=co.id, name="Region One", code="R1"), Region(company_id=co.id, name="Region Two", code="R2")
        s.add_all([r1, r2])
        await s.flush()
        c1 = Cluster(company_id=co.id, region_id=r1.id, name="Cluster One", code="C1")
        s.add(c1)
        await s.flush()
        b1 = Branch(company_id=co.id, region_id=r1.id, cluster_id=c1.id, name="Branch One", code="B1")
        b2 = Branch(company_id=co.id, region_id=r1.id, name="Branch Two", code="B2")
        b3 = Branch(company_id=co.id, region_id=r2.id, name="Branch Three", code="B3")
        s.add_all([b1, b2, b3])
        await s.flush()
        places = {"B1": b1, "B2": b2, "B3": b3, "C1": c1, "R1": r1}
        out = {"company_id": co.id, "tag": tag, "branch_id": b1.id, "b1": b1.id, "b2": b2.id, "b3": b3.id,
               "c1": c1.id, "r1": r1.id, "r2": r2.id}
        for key, role, kind, place in PEOPLE:
            code = f"{key.upper()}{tag}"
            u = User(company_id=co.id, employee_code=code, full_name=key.title(), email=f"{key}-{tag.lower()}@x.io",
                     role=role, password_hash=pw)
            if kind:
                setattr(u, f"{kind}_id", places[place].id)
            s.add(u)
            await s.flush()
            out[f"{key}_id"], out[f"{key}_code"], out[f"{key}_email"] = u.id, code, u.email
        await ensure_company_defaults(s, co.id)
        await s.commit()
    # Old names used by some tests
    out["agent_email"], out["admin_email"], out["agent_id"] = out["so1_email"], out["admin_email"], out["so1_id"]
    return out


PORTAL = {"sales_officer": "mobile", "caller": "callcentre", "master_owner": "callcentre", "sankalp_monitor": "admin",
          "mis": "admin", "admin": "admin"}


def portal_for(key: str) -> str:
    role = dict((k, r) for k, r, *_ in PEOPLE)[key]
    return PORTAL.get(role, "manage")


async def login(client, identifier, password=PASSWORD, portal=None, *, key=None):
    """login(client, t["so1_email"]) works out the portal from the email's person key."""
    key = key or identifier.split("-")[0]
    r = await client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password,
                                                       "portal": portal or portal_for(key)})
    assert r.status_code == 200, r.text
    return r.json()


async def as_(client, t: dict, key: str) -> dict:
    """Auth headers for person `key` of company `t`."""
    return auth(await login(client, t[f"{key}_email"], key=key))


def auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest_asyncio.fixture
async def tenant_a():
    return await make_company()


@pytest_asyncio.fixture
async def tenant_b():
    return await make_company()


def jpeg_bytes(color=(200, 30, 30), size=(64, 48)) -> bytes:
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


async def upload_photo(client, headers, data: bytes | None = None, **meta):
    """Full happy-path upload; returns photo_id. `headers` may be auth headers or a token dict."""
    import hashlib

    headers = auth(headers) if "access_token" in headers else headers
    data = data or jpeg_bytes()
    pid = str(uuid.uuid4())
    body = {"photo_id": pid, "mime_type": "image/jpeg", "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), **meta}
    assert (await client.post("/api/v1/uploads/initiate", json=body, headers=headers)).status_code == 200
    assert (await client.put(f"/api/v1/uploads/{pid}", content=data, headers=headers)).status_code == 200
    r = await client.post(f"/api/v1/uploads/{pid}/complete", headers=headers)
    assert r.status_code == 200, r.text
    return pid


def entry_body(key=None, **over) -> dict:
    """A valid entry: a Lead met at 09:07:06 IST on Thu 15 Oct 2026, with a GPS fix."""
    body = {
        "idempotency_key": key or uuid.uuid4().hex, "client_entry_id": uuid.uuid4().hex,
        "category": "lead", "person_name": "Ravi", "phone": "+91 98765 43210",
        "description": "Wants a home loan for a plot", "photo_ids": [],
        "submitted_at_device": "2026-10-15T09:07:06.900+05:30", "device_tz_offset_min": 330,
        "location": {"latitude": 16.5, "longitude": 80.6, "accuracy_m": 12.5,
                     "fix_at_device": "2026-10-15T09:07:07+05:30", "status": "obtained"},
    }
    body.update(over)
    return body


async def make_entry(client, headers, **over) -> dict:
    r = await client.post("/api/v1/entries", json=entry_body(**over), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
