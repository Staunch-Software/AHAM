"""Type-of-person options, review workflow, revisions and corrections."""
import json
import uuid

from sqlalchemy import select

from app.api.v1.forms import publish_version
from app.core.db import SessionLocal
from app.models import Company, SubmissionPersonType
from tests.conftest import SEED_FORM, auth, login, submission_body, upload_photo

V4 = json.loads((SEED_FORM.parent / "field_meeting_report.v4.json").read_text(encoding="utf-8"))


async def setup_v4(tenant):
    async with SessionLocal() as s:
        co = await s.get(Company, tenant["company_id"])
        await publish_version(s, co, V4, [None])
        await s.commit()


def v4_body(type_value, photos=None, key=None, **over):
    body = submission_body(form_version=4, key=key)
    e = body["answers"]["meeting_details"][0]
    e["contact_category"] = type_value
    if photos:
        e["meeting_photos"] = photos
    body.update(over)
    return body


async def types_by_label(client, adm):
    return {t["label"]: t for t in (await client.get("/api/v1/person-types", headers=auth(adm))).json()["items"]}


# ------------------------------------------------------------------ type of person
async def test_person_type_management(client, tenant_a, tenant_b):
    adm, other = await login(client, tenant_a["admin_email"]), await login(client, tenant_b["admin_email"])
    ag = await login(client, tenant_a["agent_email"])
    first = (await client.get("/api/v1/person-types", headers=auth(adm))).json()
    assert [t["label"] for t in first["items"]] == ["Customer", "Dealer", "Distributor", "Supplier", "Business Partner"]
    assert first["settings"] == {"required": True, "allow_other": False}
    assert (await client.get("/api/v1/person-types", headers=auth(ag))).status_code == 403  # admin only

    r = await client.post("/api/v1/person-types", json={"label": "Government Official"}, headers=auth(adm))
    assert r.status_code == 201 and r.json()["items"][-1]["label"] == "Government Official"
    dup = await client.post("/api/v1/person-types", json={"label": "  dealer "}, headers=auth(adm))
    assert dup.status_code == 409  # duplicate active name (case/space-insensitive)

    t = await types_by_label(client, adm)
    r = await client.patch(f"/api/v1/person-types/{t['Dealer']['id']}", json={"label": "Retail Dealer"}, headers=auth(adm))
    assert r.status_code == 200 and "Retail Dealer" in [x["label"] for x in r.json()["items"]]
    clash = await client.patch(f"/api/v1/person-types/{t['Supplier']['id']}", json={"label": "customer"}, headers=auth(adm))
    assert clash.status_code == 409

    # deactivate frees the name; re-activating a name that is now taken is refused
    await client.patch(f"/api/v1/person-types/{t['Customer']['id']}", json={"active": False}, headers=auth(adm))
    assert (await client.post("/api/v1/person-types", json={"label": "Customer"}, headers=auth(adm))).status_code == 201
    assert (await client.patch(f"/api/v1/person-types/{t['Customer']['id']}", json={"active": True}, headers=auth(adm))).status_code == 409

    # reorder
    ids = [x["id"] for x in (await client.get("/api/v1/person-types", headers=auth(adm))).json()["items"]]
    rev = list(reversed(ids))
    r = await client.put("/api/v1/person-types/order", json={"ids": rev}, headers=auth(adm))
    assert [x["id"] for x in r.json()["items"]] == rev
    assert (await client.put("/api/v1/person-types/order", json={"ids": [str(uuid.uuid4())]}, headers=auth(adm))).status_code == 422

    # settings + isolation
    r = await client.patch("/api/v1/person-types/settings", json={"allow_other": True, "required": False}, headers=auth(adm))
    assert r.json()["settings"] == {"required": False, "allow_other": True}
    assert (await client.get("/api/v1/person-types", headers=auth(other))).json()["settings"] == {"required": True, "allow_other": False}
    assert (await client.patch(f"/api/v1/person-types/{t['Supplier']['id']}", json={"label": "x"}, headers=auth(other))).status_code == 404


async def test_agents_get_active_options_and_reports_keep_labels(client, tenant_a):
    await setup_v4(tenant_a)
    adm, ag = await login(client, tenant_a["admin_email"]), await login(client, tenant_a["agent_email"])
    t = await types_by_label(client, adm)
    sync = (await client.get("/api/v1/agent/forms/sync", headers=auth(ag))).json()[0]
    field = sync["schema"]["sections"][0]["fields"][0]
    assert sync["version"] == 4 and field["key"] == "contact_category" and field["required"] is True
    assert [o["label"] for o in field["options"]] == ["Customer", "Dealer", "Distributor", "Supplier", "Business Partner"]

    # a report with a chosen type: label snapshot, per-meeting row, list shows it, filter works
    sid = (await client.post("/api/v1/submissions", json=v4_body(t["Dealer"]["id"]), headers=auth(ag))).json()["id"]
    d = (await client.get(f"/api/v1/submissions/{sid}", headers=auth(adm))).json()
    assert d["option_labels"] == {"meeting_details[0].contact_category": "Dealer"} and d["person_types"] == ["Dealer"]
    other_sid = (await client.post("/api/v1/submissions", json=v4_body(t["Supplier"]["id"]), headers=auth(ag))).json()["id"]
    f = (await client.get(f"/api/v1/submissions?person_type_id={t['Dealer']['id']}", headers=auth(adm))).json()
    assert [r["id"] for r in f["items"]] == [sid] and other_sid not in [r["id"] for r in f["items"]]

    # rename: old report keeps the label it was saved with; new reports use the new one
    await client.patch(f"/api/v1/person-types/{t['Dealer']['id']}", json={"label": "Retail Dealer"}, headers=auth(adm))
    d = (await client.get(f"/api/v1/submissions/{sid}", headers=auth(adm))).json()
    assert d["option_labels"]["meeting_details[0].contact_category"] == "Dealer"
    sid2 = (await client.post("/api/v1/submissions", json=v4_body(t["Dealer"]["id"]), headers=auth(ag))).json()["id"]
    assert (await client.get(f"/api/v1/submissions/{sid2}", headers=auth(adm))).json()["person_types"] == ["Retail Dealer"]

    # deactivate: gone from new downloads, still accepted from an offline agent that has it cached
    await client.patch(f"/api/v1/person-types/{t['Supplier']['id']}", json={"active": False}, headers=auth(adm))
    opts = (await client.get("/api/v1/agent/forms/sync", headers=auth(ag))).json()[0]["schema"]["sections"][0]["fields"][0]["options"]
    assert "Supplier" not in [o["label"] for o in opts]
    ok = await client.post("/api/v1/submissions", json=v4_body(t["Supplier"]["id"]), headers=auth(ag))
    assert ok.status_code == 201
    assert (await client.post("/api/v1/submissions", json=v4_body(str(uuid.uuid4())), headers=auth(ag))).status_code == 422
    assert (await client.post("/api/v1/submissions", json=v4_body("Dealer"), headers=auth(ag))).status_code == 422  # names are not ids


async def test_other_custom_value_and_required_setting(client, tenant_a):
    await setup_v4(tenant_a)
    adm, ag = await login(client, tenant_a["admin_email"]), await login(client, tenant_a["agent_email"])
    custom = v4_body("other:Government Official")
    r = await client.post("/api/v1/submissions", json=custom, headers=auth(ag))
    assert r.status_code == 422  # Other is off by default
    await client.patch("/api/v1/person-types/settings", json={"allow_other": True}, headers=auth(adm))
    assert (await client.get("/api/v1/agent/forms/sync", headers=auth(ag))).json()[0]["schema"]["sections"][0]["fields"][0]["allow_other"] is True
    r = await client.post("/api/v1/submissions", json=custom, headers=auth(ag))
    assert r.status_code == 201, r.text
    d = (await client.get(f"/api/v1/submissions/{r.json()['id']}", headers=auth(adm))).json()
    assert d["person_types"] == ["Government Official"]
    async with SessionLocal() as s:
        row = (await s.execute(select(SubmissionPersonType).where(SubmissionPersonType.submission_id == uuid.UUID(r.json()["id"])))).scalar_one()
    assert row.person_type_id is None and row.other_text == "Government Official"
    assert (await client.post("/api/v1/submissions", json=v4_body("other:   "), headers=auth(ag))).status_code == 422
    # not required => a meeting without a type is accepted
    await client.patch("/api/v1/person-types/settings", json={"required": False}, headers=auth(adm))
    blank = v4_body("x")
    blank["answers"]["meeting_details"][0].pop("contact_category")
    assert (await client.post("/api/v1/submissions", json=blank, headers=auth(ag))).status_code == 201


# ------------------------------------------------------------------ review + corrections
async def reasons(client, adm):
    return {r["code"]: r for r in (await client.get("/api/v1/review-reasons", headers=auth(adm))).json()["items"]}


async def submit_report(client, ag, t, photos=None):
    r = await client.post("/api/v1/submissions", json=v4_body(t["Customer"]["id"], photos=photos), headers=auth(ag))
    assert r.status_code == 201, r.text
    return r.json()


async def test_reject_requires_reason_and_agent_sees_feedback(client, tenant_a):
    await setup_v4(tenant_a)
    adm, ag = await login(client, tenant_a["admin_email"]), await login(client, tenant_a["agent_email"])
    t = await types_by_label(client, adm)
    rc = await reasons(client, adm)
    assert list(rc)[:3] == ["missing_information", "unclear_photo", "incorrect_details"]
    rep = await submit_report(client, ag, t)
    assert rep["reference"].startswith("FS-") and rep["revision"] == 1
    url = f"/api/v1/submissions/{rep['id']}/reviews"

    assert (await client.post(url, json={"decision": "rejected"}, headers=auth(adm))).status_code == 422  # reason needed
    assert (await client.post(url, json={"decision": "rejected", "reason_code": "nope"}, headers=auth(adm))).status_code == 422
    assert (await client.post(url, json={"decision": "rejected", "reason_code": "other"}, headers=auth(adm))).status_code == 422  # needs text
    assert (await client.post(url, json={"decision": "approved"}, headers=auth(ag))).status_code == 403

    r = await client.post(url, headers=auth(adm), json={
        "decision": "rejected", "reason_code": "unclear_photo", "comment": "Upload a clearer photo for the second meeting.",
        "flags": [{"path": "meeting_details[0]", "note": "Photo is blurry"}]})
    assert r.status_code == 200 and r.json()["status"] == "rejected"

    up = (await client.get("/api/v1/agent/reports/updates", headers=auth(ag))).json()["items"]
    assert len(up) == 1 and up[0]["id"] == rep["id"] and up[0]["review_status"] == "rejected"
    assert up[0]["reason_label"] == "Unclear photo" and up[0]["comment"].startswith("Upload a clearer")
    assert up[0]["flags"] == [{"path": "meeting_details[0]", "note": "Photo is blurry"}]
    since = {"since": up[0]["reviewed_at"]}  # passed as a parameter so '+' in the timezone is encoded
    assert (await client.get("/api/v1/agent/reports/updates", params=since, headers=auth(ag))).json()["items"] == []
    # another agent's feed is separate; the reason label is a snapshot (renaming the reason later does not rewrite it)
    await client.patch(f"/api/v1/review-reasons/{rc['unclear_photo']['id']}", json={"label": "Blurry photo"}, headers=auth(adm))
    d = (await client.get(f"/api/v1/submissions/{rep['id']}", headers=auth(adm))).json()
    assert d["reviews"][0]["reason_label"] == "Unclear photo" and d["review_status"] == "rejected"


async def test_correction_creates_new_revision_and_keeps_history(client, tenant_a):
    await setup_v4(tenant_a)
    adm, ag = await login(client, tenant_a["admin_email"]), await login(client, tenant_a["agent_email"])
    t = await types_by_label(client, adm)
    p1, p2 = await upload_photo(client, ag), await upload_photo(client, ag)
    rep = await submit_report(client, ag, t, photos=[p1])
    url = f"/api/v1/submissions/{rep['id']}/reviews"
    corr = {"submission_id": rep["id"], "base_revision": 1}

    # cannot correct a report that was not rejected
    body = v4_body(t["Customer"]["id"], photos=[p1, p2], corrects=corr)
    r = await client.post("/api/v1/submissions", json=body, headers=auth(ag))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "report_not_rejected"

    await client.post(url, json={"decision": "rejected", "reason_code": "evidence_required", "comment": "Add a second photo."}, headers=auth(adm))
    ok = await client.post("/api/v1/submissions", json=body, headers=auth(ag))
    assert ok.status_code == 201, ok.text
    rev2 = ok.json()
    assert rev2["revision"] == 2 and rev2["reference"] == rep["reference"] and rev2["root_id"] == rep["root_id"] and rev2["id"] != rep["id"]

    # replaying the same request is idempotent; a different (stale) correction is refused with an explanation
    again = await client.post("/api/v1/submissions", json=body, headers=auth(ag))
    assert again.status_code == 201 and again.json()["id"] == rev2["id"] and again.json()["duplicate"] is True
    stale = v4_body(t["Customer"]["id"], photos=[p1], corrects=corr, key=uuid.uuid4().hex)
    r = await client.post("/api/v1/submissions", json=stale, headers=auth(ag))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "report_changed"

    # old revision untouched and marked superseded; the new one is in the review queue with BOTH photos
    old = (await client.get(f"/api/v1/submissions/{rep['id']}", headers=auth(adm))).json()
    new = (await client.get(f"/api/v1/submissions/{rev2['id']}", headers=auth(adm))).json()
    assert old["is_latest"] is False and old["review_status"] == "rejected" and len(old["photos"]) == 1
    assert new["is_latest"] is True and new["review_status"] == "pending" and new["revision"] == 2 and len(new["photos"]) == 2
    assert [r["revision"] for r in new["revisions"]] == [1, 2]
    assert [x["decision"] for x in new["reviews"]] == ["rejected"] and new["reviews"][0]["revision"] == 1  # history spans revisions
    listed = (await client.get("/api/v1/submissions", headers=auth(adm))).json()["items"]
    assert [x["id"] for x in listed] == [rev2["id"]]  # superseded versions are hidden by default
    all_rows = (await client.get("/api/v1/submissions?latest_only=false", headers=auth(adm))).json()["items"]
    assert {x["id"] for x in all_rows} == {rep["id"], rev2["id"]}
    # the old revision can no longer be reviewed; the new one can
    assert (await client.post(url, json={"decision": "approved"}, headers=auth(adm))).status_code == 409
    done = await client.post(f"/api/v1/submissions/{rev2['id']}/reviews", json={"decision": "approved"}, headers=auth(adm))
    assert done.status_code == 200
    # approval is final until reopened with a reason
    r2 = f"/api/v1/submissions/{rev2['id']}"
    assert (await client.post(f"{r2}/reviews", json={"decision": "rejected", "reason_code": "other", "comment": "x"}, headers=auth(adm))).status_code == 409
    assert (await client.post(f"{r2}/reopen", json={"comment": "x"}, headers=auth(adm))).status_code == 422
    assert (await client.post(f"{r2}/reopen", json={"comment": "Client asked for a recheck"}, headers=auth(adm))).json()["status"] == "pending"
    hist = (await client.get(r2, headers=auth(adm))).json()["reviews"]
    assert [h["decision"] for h in hist] == ["rejected", "approved", "reopened"]


async def test_correction_access_rules_and_photo_reuse_limits(client, tenant_a, tenant_b):
    await setup_v4(tenant_a)
    adm, ag = await login(client, tenant_a["admin_email"]), await login(client, tenant_a["agent_email"])
    t = await types_by_label(client, adm)
    rep = await submit_report(client, ag, t, photos=[await upload_photo(client, ag)])
    await client.post(f"/api/v1/submissions/{rep['id']}/reviews", json={"decision": "rejected", "reason_code": "missing_information", "comment": "x"}, headers=auth(adm))
    corr = {"submission_id": rep["id"], "base_revision": 1}
    # a photo from a DIFFERENT report cannot be pulled into the correction
    foreign = await submit_report(client, ag, t, photos=[await upload_photo(client, ag)])
    fdet = (await client.get(f"/api/v1/submissions/{foreign['id']}", headers=auth(adm))).json()
    stolen = v4_body(t["Customer"]["id"], photos=[fdet["photos"][0]["photo_id"]], corrects=corr)
    r = await client.post("/api/v1/submissions", json=stolen, headers=auth(ag))
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["message"] == "photo already attached"
    # another company's agent cannot correct this report
    await setup_v4(tenant_b)
    other = await login(client, tenant_b["agent_email"])
    r = await client.post("/api/v1/submissions", json=v4_body("x", corrects=corr), headers=auth(other))
    assert r.status_code == 404 and r.json()["detail"]["code"] == "report_not_found"
    # another agent of the SAME company cannot correct it either
    async with SessionLocal() as s:
        from app.models import User
        from app.security.passwords import hash_password
        s.add(User(company_id=tenant_a["company_id"], employee_code="G9", full_name="Colleague", email=f"col-{uuid.uuid4().hex[:6]}@x.io",
                   role="agent", branch_id=tenant_a["branch_id"], password_hash=hash_password("password123")))
        await s.commit()
        email = (await s.execute(select(User.email).where(User.employee_code == "G9", User.company_id == tenant_a["company_id"]))).scalar_one()
    colleague = await login(client, email)
    r = await client.post("/api/v1/submissions", json=v4_body("x", corrects=corr), headers=auth(colleague))
    assert r.status_code == 404


async def test_references_are_unique_and_sequential(client, tenant_a):
    await setup_v4(tenant_a)
    adm, ag = await login(client, tenant_a["admin_email"]), await login(client, tenant_a["agent_email"])
    t = await types_by_label(client, adm)
    refs = [(await submit_report(client, ag, t))["reference"] for _ in range(3)]
    nums = [int(r.rsplit("-", 1)[1]) for r in refs]
    assert len(set(refs)) == 3 and nums == [nums[0], nums[0] + 1, nums[0] + 2]
    assert all(r.startswith("FS-20") for r in refs)
