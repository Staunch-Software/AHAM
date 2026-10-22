import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
import pytest_asyncio

TEST_DB = "fieldsync_test"
BASE_URL = os.environ.get(
    "TEST_DATABASE_SERVER", "postgresql+asyncpg://fieldsync:fieldsync_dev@localhost:5433"
)
os.environ["DATABASE_URL"] = f"{BASE_URL}/{TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["GEOCODER"] = "none"  # no network lookups in tests (geocoding is tested with fakes)
os.environ["INTERNAL_API_KEY"] = "test-internal-key"
os.environ["STORAGE_ROOT"] = str(Path(__file__).parent / ".storage")
SEED_FORM = Path(__file__).resolve().parents[2] / "database" / "seed" / "field_meeting_report.v1.json"

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


async def make_company(client_session_factory=None):
    from app.core.db import SessionLocal
    from app.models import Branch, Company, User
    from app.security.passwords import hash_password

    tag = uuid.uuid4().hex[:8]
    async with SessionLocal() as s:
        co = Company(name=f"Co {tag}", code=f"co-{tag}")
        s.add(co)
        await s.flush()
        br = Branch(company_id=co.id, name="HQ", code="HQ")
        s.add(br)
        await s.flush()
        admin = User(
            company_id=co.id, employee_code="A1", full_name="Admin", email=f"admin-{tag}@x.io",
            role="admin", password_hash=hash_password("password123"),
        )
        agent = User(
            company_id=co.id, branch_id=br.id, employee_code="G1", full_name="Agent",
            email=f"agent-{tag}@x.io", role="agent", password_hash=hash_password("password123"),
        )
        s.add_all([admin, agent])
        await s.flush()
        from app.api.v1.forms import publish_version
        await publish_version(s, co, json.loads(SEED_FORM.read_text(encoding="utf-8")), [None])
        from app.services.workflow import ensure_company_defaults
        await ensure_company_defaults(s, co.id)
        await s.commit()
        return {
            "company_id": co.id, "branch_id": br.id,
            "admin_email": admin.email, "agent_email": agent.email,
            "agent_id": agent.id, "admin_id": admin.id,
        }


async def login(client, email, password="password123"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


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


async def upload_photo(client, tokens, data: bytes | None = None, **meta):
    """Full happy-path upload; returns photo_id."""
    import hashlib

    data = data or jpeg_bytes()
    pid = str(uuid.uuid4())
    body = {"photo_id": pid, "mime_type": "image/jpeg", "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), **meta}
    assert (await client.post("/api/v1/uploads/initiate", json=body, headers=auth(tokens))).status_code == 200
    assert (await client.put(f"/api/v1/uploads/{pid}", content=data, headers=auth(tokens))).status_code == 200
    r = await client.post(f"/api/v1/uploads/{pid}/complete", headers=auth(tokens))
    assert r.status_code == 200, r.text
    return pid


def submission_body(photo_id=None, key=None, **over):
    entry = {"contact_category": "Dealer", "contact_name": "Ravi", "meeting_date": "2026-10-10",
             "meeting_description": "Discussed renewal"}
    if photo_id:
        entry["meeting_photo"] = photo_id
    body = {
        "idempotency_key": key or uuid.uuid4().hex, "client_submission_id": uuid.uuid4().hex,
        "form_id": "field_meeting_report", "form_version": 1,
        "answers": {"meeting_details": [entry]},
        "submitted_at_device": "2026-10-10T10:15:00+05:30", "device_tz_offset_min": 330,
        "location": {"latitude": 16.5, "longitude": 80.6, "accuracy_m": 12.5,
                     "fix_at_device": "2026-10-10T10:15:02+05:30", "status": "obtained"},
    }
    body.update(over)
    return body
