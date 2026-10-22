import copy
import json

import pytest

from app.services.form_schema import SchemaError, validate_answers, validate_schema
from tests.conftest import SEED_FORM, auth, login

SCHEMA = json.loads(SEED_FORM.read_text(encoding="utf-8"))


def test_seed_schema_is_valid():
    validate_schema(SCHEMA)


@pytest.mark.parametrize("mutate", [
    lambda s: s["sections"][0]["fields"][0].update(type="javascript"),
    lambda s: s["sections"][0]["fields"][0].update(validation={"eval": "1+1"}),
    lambda s: s["sections"][0]["fields"][0].update(validation={"pattern": "(["}),
    lambda s: s["sections"][0]["fields"][0].update(visible_if={"field": "x", "op": "exec"}),
    lambda s: s["sections"][0]["fields"].append(dict(s["sections"][0]["fields"][0])),
    lambda s: s["sections"][0].update(min_items=5, max_items=2),
    lambda s: s.update(sections=[]),
])
def test_bad_schemas_rejected(mutate):
    bad = copy.deepcopy(SCHEMA)
    mutate(bad)
    with pytest.raises(SchemaError):
        validate_schema(bad)


def test_answer_validation_reports_stable_field_ids():
    errs = validate_answers(SCHEMA, {"meeting_details": [{"contact_name": "x", "meeting_date": "not-a-date",
                                                         "contact_whatsapp": "abc"}]})
    by = {e["field_id"]: e["message"] for e in errs}
    assert by["contact_category"] == "required"
    assert by["meeting_date"] == "invalid value"
    assert by["contact_whatsapp"] == "invalid phone number"
    assert by["meeting_description"] == "required"


def test_repeatable_bounds_and_unknown_keys():
    assert validate_answers(SCHEMA, {"meeting_details": []})[0]["message"].startswith("entries must be")
    e = validate_answers(SCHEMA, {"meeting_details": [{"bogus": 1}], "other": {}})
    assert {x["message"] for x in e} >= {"unknown field", "unknown section"}


def test_conditional_visibility():
    s = copy.deepcopy(SCHEMA)
    s["sections"][0]["fields"].append(
        {"id": "why", "key": "why", "label": "Why", "type": "text", "required": True,
         "visible_if": {"field": "contact_category", "op": "eq", "value": "Other"}})
    entry = {"contact_category": "Dealer", "contact_name": "a", "meeting_date": "2026-01-01",
             "meeting_description": "d"}
    assert validate_answers(s, {"meeting_details": [entry]}) == []
    entry["contact_category"] = "Other"
    assert validate_answers(s, {"meeting_details": [entry]})[0]["field_id"] == "why"


async def test_agent_form_delivery_and_admin_blocked(client, tenant_a, tenant_b):
    t = await login(client, tenant_a["agent_email"])
    forms = (await client.get("/api/v1/agent/forms", headers=auth(t))).json()
    assert forms == [{"form_id": "field_meeting_report", "title": "Field Meeting Report", "version": 1}]
    v = await client.get("/api/v1/agent/forms/field_meeting_report/versions/1", headers=auth(t))
    assert v.json()["schema"]["sections"][0]["repeatable"] is True
    assert (await client.get("/api/v1/agent/forms/field_meeting_report/versions/9", headers=auth(t))).status_code == 404
    assert len((await client.get("/api/v1/agent/forms/sync", headers=auth(t))).json()) == 1
    adm = await login(client, tenant_a["admin_email"])
    assert (await client.get("/api/v1/agent/forms", headers=auth(adm))).status_code == 403


async def test_internal_endpoint_protected(client, tenant_a):
    adm = await login(client, tenant_a["admin_email"])
    url = "/api/v1/internal/forms"
    body = {"company_code": "x", "schema": SCHEMA}
    assert (await client.post(url, json=body, headers=auth(adm))).status_code == 403  # bearer token is not enough
    assert (await client.post(url, json=body, headers={"X-Internal-Key": "wrong"})).status_code == 403
    ok = copy.deepcopy(SCHEMA)
    ok["version"] = 2
    from app.core.db import SessionLocal
    from app.models import Company
    from sqlalchemy import select
    async with SessionLocal() as s:
        code = (await s.execute(select(Company.code).where(Company.id == tenant_a["company_id"]))).scalar_one()
    r = await client.post(url, json={"company_code": code, "schema": ok}, headers={"X-Internal-Key": "test-internal-key"})
    assert r.status_code == 201
    again = await client.post(url, json={"company_code": code, "schema": ok}, headers={"X-Internal-Key": "test-internal-key"})
    assert again.status_code == 409  # versions are immutable / monotonic
    bad = copy.deepcopy(ok); bad["version"] = 3; bad["sections"][0]["fields"][0]["type"] = "js"
    r = await client.post(url, json={"company_code": code, "schema": bad}, headers={"X-Internal-Key": "test-internal-key"})
    assert r.status_code == 422


def test_non_development_env_requires_strong_secrets():
    import pytest
    from app.core.config import Settings
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production", jwt_secret="change-me-to-a-long-random-string", file_url_secret="x" * 40)
    ok = Settings(_env_file=None, app_env="production", jwt_secret="a" * 40, file_url_secret="b" * 40)
    assert ok.app_env == "production"
    Settings(_env_file=None, app_env="development", jwt_secret="short")  # dev is allowed


async def test_v3_form_has_no_manual_time_multiple_photos_and_mapping_consistent(client, tenant_a):
    """v3: no typed photo time; several photos per meeting (max 5). Older versions stay deliverable/accepted."""
    import uuid
    from app.api.v1.forms import publish_version
    from app.core.db import SessionLocal
    from app.models import Company
    from tests.conftest import submission_body, upload_photo
    v2 = json.loads((SEED_FORM.parent / "field_meeting_report.v2.json").read_text(encoding="utf-8"))
    v3 = json.loads((SEED_FORM.parent / "field_meeting_report.v3.json").read_text(encoding="utf-8"))
    validate_schema(v2)
    validate_schema(v3)
    keys3 = {f["key"] for f in v3["sections"][0]["fields"]}
    assert "keka_photo_time" not in keys3 and not any(f["type"] == "time" for f in v3["sections"][0]["fields"])
    async with SessionLocal() as s:
        co = await s.get(Company, tenant_a["company_id"])
        await publish_version(s, co, v2, [None])
        await publish_version(s, co, v3, [None])
        await s.commit()
    ag = await login(client, tenant_a["agent_email"])
    adm = await login(client, tenant_a["admin_email"])
    assert (await client.get("/api/v1/agent/forms", headers=auth(ag))).json()[0]["version"] == 3

    # three photos on one meeting, each with its own capture time and location
    pids = []
    for i, (lat, lon) in enumerate([(14.44, 79.98), (14.45, 79.99), (14.46, 80.0)]):
        pids.append(await upload_photo(client, ag, photo_captured_at_device=f"2026-10-10T10:0{i}:00+05:30",
                                       latitude=lat, longitude=lon, accuracy_m=6, location_status="obtained"))
    body = submission_body(form_version=3)
    entry = body["answers"]["meeting_details"][0]
    entry["meeting_photos"] = pids
    ok = await client.post("/api/v1/submissions", json=body, headers=auth(ag))
    assert ok.status_code == 201, ok.text
    d = (await client.get(f"/api/v1/submissions/{ok.json()['id']}", headers=auth(adm))).json()
    assert d["photo_count"] == 3 and len(d["photos"]) == 3
    assert sorted(p["photo_capture_latitude"] for p in d["photos"]) == [14.44, 14.45, 14.46]
    assert len({p["photo_captured_at_device"] for p in d["photos"]}) == 3  # each photo keeps its own time

    # limit, duplicates and the removed manual-time field are rejected
    six = [await upload_photo(client, ag) for _ in range(6)]
    over = submission_body(form_version=3, key=uuid.uuid4().hex)
    over["answers"]["meeting_details"][0]["meeting_photos"] = six
    r = await client.post("/api/v1/submissions", json=over, headers=auth(ag))
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["message"] == "at most 5 photos"
    typed = submission_body(form_version=3, key=uuid.uuid4().hex)
    typed["answers"]["meeting_details"][0]["keka_photo_time"] = "10:02"
    r = await client.post("/api/v1/submissions", json=typed, headers=auth(ag))
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["message"] == "unknown field"
    # older versions are still accepted (offline drafts made earlier)
    assert (await client.post("/api/v1/submissions", json=submission_body(form_version=1), headers=auth(ag))).status_code == 201
    v2b = submission_body(form_version=2)
    v2b["answers"]["meeting_details"][0]["keka_photo_time"] = "10:02"
    assert (await client.post("/api/v1/submissions", json=v2b, headers=auth(ag))).status_code == 201

    mapping = json.loads((SEED_FORM.parent / "field_meeting_report.mapping.json").read_text(encoding="utf-8"))
    for c in mapping["columns"]:
        assert c["status"] in {"mapped", "derived", "unmapped"}
        if c["status"] == "unmapped":
            assert c["target"] is None and c["question"]  # never guessed
    mentioned = " ".join(c["target"] or "" for c in mapping["columns"])
    assert all(k in mentioned for k in keys3 - {"meeting_photos"})  # the workbook has no photo column
    assert "meeting_photos" in mapping["photos"]


async def test_bootstrap_creates_company_admin_forms_and_refuses_duplicates():
    import uuid
    import pytest
    from sqlalchemy import select
    from app.bootstrap import bootstrap
    from app.core.db import SessionLocal
    from app.models import Branch, Company
    tag = uuid.uuid4().hex[:8]
    kw = dict(company_name=f"Boot {tag}", company_code=f"boot-{tag}", admin_name="Boss", admin_email=f"boss-{tag}@x.io",
              admin_employee_code="A1", password="a-long-enough-password", with_branches=True)
    res = await bootstrap(**kw)
    assert res["form_versions"] == [1, 2, 3, 4] and len(res["branches"]) == 9
    async with SessionLocal() as s:
        co = (await s.execute(select(Company).where(Company.code == kw["company_code"]))).scalar_one()
        n = len((await s.execute(select(Branch).where(Branch.company_id == co.id))).scalars().all())
    assert n == 9
    with pytest.raises(SystemExit):
        await bootstrap(**kw)  # same code/email -> refused, nothing changed
    with pytest.raises(SystemExit):
        await bootstrap(**{**kw, "company_code": f"other-{tag}", "admin_email": f"o-{tag}@x.io", "password": "short"})
