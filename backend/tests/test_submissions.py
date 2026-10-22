import asyncio
import hashlib
import json
import uuid

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models import OutboxEvent, Submission, SubmissionPhoto, User
from app.security.passwords import hash_password
from app.workers.outbox import hub, process_outbox_once
from tests.conftest import auth, jpeg_bytes, login, submission_body, upload_photo

CAPTURE = {
    "photo_captured_at_device": "2026-10-10T10:00:00+05:30",
    "latitude": 14.4426, "longitude": 79.9865, "accuracy_m": 8.0,
    "location_fix_at_device": "2026-10-10T10:00:01+05:30", "location_status": "obtained",
    "location_source": "gps",
}


async def _outbox_row(sid):
    async with SessionLocal() as s:
        return (await s.execute(
            select(OutboxEvent).where(OutboxEvent.payload["submission_id"].astext == sid))).scalar_one()


async def test_online_submission_and_admin_view(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    adm = await login(client, tenant_a["admin_email"])
    pid = await upload_photo(client, ag, **CAPTURE)
    r = await client.post("/api/v1/submissions", json=submission_body(pid), headers=auth(ag))
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["status"] == "accepted" and rec["duplicate"] is False

    lst = (await client.get("/api/v1/submissions", headers=auth(adm))).json()
    assert lst["total"] == 1 and lst["items"][0]["photo_count"] == 1 and lst["items"][0]["has_location"]
    d = (await client.get(f"/api/v1/submissions/{rec['id']}", headers=auth(adm))).json()
    assert d["answers"]["meeting_details"][0]["meeting_photo"] == pid
    url = d["photos"][0]["url"]
    img = await client.get(url)
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert (await client.get(url[:-4] + "0000")).status_code == 403
    assert (await client.get(f"/api/v1/files/{pid}?variant=original&exp=1&sig=abc")).status_code == 403
    assert (await client.get("/api/v1/agent/submissions", headers=auth(ag))).json()["total"] == 1


async def test_scenario_e_time_and_location_separation(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    adm = await login(client, tenant_a["admin_email"])
    pid = await upload_photo(client, ag, **CAPTURE)
    sid = (await client.post("/api/v1/submissions", json=submission_body(pid), headers=auth(ag))).json()["id"]
    d = (await client.get(f"/api/v1/submissions/{sid}", headers=auth(adm))).json()
    p, sl = d["photos"][0], d["submission_location"]
    assert p["photo_capture_latitude"] == 14.4426 and sl["latitude"] == 16.5
    assert p["photo_captured_at_device"].startswith("2026-10-10T04:30:00")  # 10:00+05:30 in UTC
    assert d["submitted_at_device"].startswith("2026-10-10T04:45:00")
    assert d["received_at_server"] and d["accepted_at_server"]
    assert d["received_at_server"] <= d["accepted_at_server"]
    assert not d["received_at_server"].startswith("2026-10-10T04:45")  # server time is its own event
    assert p["photo_location_status"] == "obtained" and d["device_tz_offset_min"] == 330


async def test_location_unavailable_is_not_zero(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    adm = await login(client, tenant_a["admin_email"])
    pid = await upload_photo(client, ag, location_status="permission_denied")
    body = submission_body(pid, location={"status": "timeout"})
    sid = (await client.post("/api/v1/submissions", json=body, headers=auth(ag))).json()["id"]
    d = (await client.get(f"/api/v1/submissions/{sid}", headers=auth(adm))).json()
    assert d["submission_location"]["latitude"] is None and d["submission_location"]["status"] == "timeout"
    assert d["photos"][0]["photo_capture_latitude"] is None
    assert d["photos"][0]["photo_location_status"] == "permission_denied"
    bad = await client.post("/api/v1/submissions", headers=auth(ag),
                            json=submission_body(key="k" * 12, location={"latitude": 95, "longitude": 0}))
    assert bad.status_code == 422


async def test_scenario_d_idempotent_retry(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    body = submission_body(key="same-key-123")
    first = await client.post("/api/v1/submissions", json=body, headers=auth(ag))
    rest = await asyncio.gather(*[client.post("/api/v1/submissions", json=body, headers=auth(ag)) for _ in range(5)])
    assert first.status_code == 201 and all(r.status_code in (200, 201) for r in rest)
    assert {r.json()["id"] for r in rest} == {first.json()["id"]}
    async with SessionLocal() as s:
        n = (await s.execute(select(func.count()).select_from(Submission)
                             .where(Submission.idempotency_key == "same-key-123"))).scalar_one()
        ob = (await s.execute(select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.payload["submission_id"].astext == first.json()["id"]))).scalar_one()
    assert n == 1 and ob == 1
    changed = submission_body(key="same-key-123", submitted_at_device="2026-10-11T00:00:00Z")
    assert (await client.post("/api/v1/submissions", json=changed, headers=auth(ag))).status_code == 409


async def test_scenario_c_interrupted_upload_resumes(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    data = jpeg_bytes(size=(800, 600))
    n = len(data)
    pid, sha = str(uuid.uuid4()), hashlib.sha256(data).hexdigest()
    init = {"photo_id": pid, "mime_type": "image/jpeg", "size_bytes": n, "sha256": sha}
    await client.post("/api/v1/uploads/initiate", json=init, headers=auth(ag))
    half = n // 2
    r = await client.put(f"/api/v1/uploads/{pid}", content=data[:half],
                         headers={**auth(ag), "Content-Range": f"bytes 0-{half-1}/{n}"})
    assert r.json()["received_bytes"] == half
    again = (await client.post("/api/v1/uploads/initiate", json=init, headers=auth(ag))).json()
    assert again["received_bytes"] == half
    assert (await client.post(f"/api/v1/uploads/{pid}/complete", headers=auth(ag))).status_code == 409
    wrong = await client.put(f"/api/v1/uploads/{pid}", content=data[half:],
                             headers={**auth(ag), "Content-Range": f"bytes 5-{4 + n - half}/{n}"})
    assert wrong.status_code == 409
    ok = await client.put(f"/api/v1/uploads/{pid}", content=data[half:],
                          headers={**auth(ag), "Content-Range": f"bytes {half}-{n-1}/{n}"})
    assert ok.status_code == 200
    done = await client.post(f"/api/v1/uploads/{pid}/complete", headers=auth(ag))
    assert done.json()["upload_status"] == "complete"
    assert (await client.post(f"/api/v1/uploads/{pid}/complete", headers=auth(ag))).status_code == 200
    async with SessionLocal() as s:
        rows = (await s.execute(select(SubmissionPhoto).where(SubmissionPhoto.id == uuid.UUID(pid)))).scalars().all()
    assert len(rows) == 1 and rows[0].sha256 == sha and rows[0].size_bytes == n


async def test_upload_validation(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    data = jpeg_bytes()
    base = {"mime_type": "image/jpeg", "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    pid = str(uuid.uuid4())
    await client.post("/api/v1/uploads/initiate", json={**base, "photo_id": pid, "sha256": "0" * 64}, headers=auth(ag))
    await client.put(f"/api/v1/uploads/{pid}", content=data, headers=auth(ag))
    assert (await client.post(f"/api/v1/uploads/{pid}/complete", headers=auth(ag))).status_code == 422
    r = await client.post("/api/v1/uploads/initiate",
                          json={**base, "photo_id": str(uuid.uuid4()), "mime_type": "text/html"}, headers=auth(ag))
    assert r.status_code == 422
    r = await client.post("/api/v1/uploads/initiate",
                          json={**base, "photo_id": str(uuid.uuid4()), "size_bytes": 10**9}, headers=auth(ag))
    assert r.status_code == 413
    junk = b"not an image at all"
    pid2 = str(uuid.uuid4())
    await client.post("/api/v1/uploads/initiate", headers=auth(ag), json={
        "photo_id": pid2, "mime_type": "image/jpeg", "size_bytes": len(junk),
        "sha256": hashlib.sha256(junk).hexdigest()})
    await client.put(f"/api/v1/uploads/{pid2}", content=junk, headers=auth(ag))
    assert (await client.post(f"/api/v1/uploads/{pid2}/complete", headers=auth(ag))).status_code == 422


async def test_submission_validation_errors_use_field_ids(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    body = submission_body()
    body["answers"]["meeting_details"][0].pop("contact_name")
    r = await client.post("/api/v1/submissions", json=body, headers=auth(ag))
    assert r.status_code == 422
    assert r.json()["detail"]["errors"][0]["field_id"] == "contact_name"
    stale = await client.post("/api/v1/submissions", json=submission_body(form_version=7), headers=auth(ag))
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "schema_outdated"
    unfinished = await client.post("/api/v1/submissions", json=submission_body(str(uuid.uuid4())), headers=auth(ag))
    assert unfinished.status_code == 422


async def test_scenario_f_permissions(client, tenant_a, tenant_b):
    a_ag, a_adm = await login(client, tenant_a["agent_email"]), await login(client, tenant_a["admin_email"])
    b_adm, b_ag = await login(client, tenant_b["admin_email"]), await login(client, tenant_b["agent_email"])
    pid = await upload_photo(client, a_ag)
    sid = (await client.post("/api/v1/submissions", json=submission_body(pid), headers=auth(a_ag))).json()["id"]
    for t in (b_adm, b_ag):
        assert (await client.get(f"/api/v1/submissions/{sid}", headers=auth(t))).status_code == 404
        assert (await client.get(f"/api/v1/photos/{pid}/url", headers=auth(t))).status_code == 404
        assert (await client.get(f"/api/v1/submissions/{sid}/photos", headers=auth(t))).status_code == 404
    assert (await client.get("/api/v1/submissions", headers=auth(b_adm))).json()["total"] == 0
    async with SessionLocal() as s:
        s.add(User(company_id=tenant_a["company_id"], employee_code="G2", full_name="Other",
                   email=f"other-{uuid.uuid4().hex[:6]}@x.io", role="agent", branch_id=tenant_a["branch_id"],
                   password_hash=hash_password("password123")))
        await s.commit()
        email = (await s.execute(select(User.email).where(User.employee_code == "G2",
                                                           User.company_id == tenant_a["company_id"]))).scalar_one()
    other = await login(client, email)
    assert (await client.get(f"/api/v1/submissions/{sid}", headers=auth(other))).status_code == 404
    assert (await client.get(f"/api/v1/photos/{pid}/url", headers=auth(other))).status_code == 404
    assert (await client.get("/api/v1/agent/submissions", headers=auth(other))).json()["total"] == 0
    assert (await client.post("/api/v1/submissions", json=submission_body(pid), headers=auth(other))).status_code == 422
    assert (await client.get("/api/v1/submissions", headers=auth(a_ag))).status_code == 403
    rv = {"decision": "approved"}
    assert (await client.post(f"/api/v1/submissions/{sid}/reviews", json=rv, headers=auth(a_ag))).status_code == 403
    assert (await client.post("/api/v1/submissions", json=submission_body(), headers=auth(a_adm))).status_code == 403
    assert (await client.post(f"/api/v1/submissions/{sid}/reviews", json=rv, headers=auth(b_adm))).status_code == 404
    ok = await client.post(f"/api/v1/submissions/{sid}/reviews", json=rv, headers=auth(a_adm))
    assert ok.json()["status"] == "approved"
    spoof = await client.post("/api/v1/submissions", headers=auth(a_ag),
                              json=submission_body(branch_id=str(uuid.uuid4())))
    assert spoof.status_code == 403


async def test_filters_and_pagination(client, tenant_a):
    ag, adm = await login(client, tenant_a["agent_email"]), await login(client, tenant_a["admin_email"])
    for i in range(3):
        loc = {"status": "unavailable"} if i == 0 else submission_body()["location"]
        await client.post("/api/v1/submissions", json=submission_body(location=loc), headers=auth(ag))
    p1 = (await client.get("/api/v1/submissions?page_size=2", headers=auth(adm))).json()
    p2 = (await client.get("/api/v1/submissions?page_size=2&page=2", headers=auth(adm))).json()
    assert p1["total"] == 3 and len(p1["items"]) == 2 and len(p2["items"]) == 1
    assert not {i["id"] for i in p1["items"]} & {i["id"] for i in p2["items"]}
    assert (await client.get("/api/v1/submissions?has_location=false", headers=auth(adm))).json()["total"] == 1
    assert (await client.get(f"/api/v1/submissions?agent_id={uuid.uuid4()}", headers=auth(adm))).json()["total"] == 0
    q = "date_from=2000-01-01&form_id=field_meeting_report&review_status=pending"
    assert (await client.get(f"/api/v1/submissions?{q}", headers=auth(adm))).json()["total"] == 3


async def test_outbox_publishes_to_company_subscribers_only(client, tenant_a, tenant_b):
    ag = await login(client, tenant_a["agent_email"])
    qa, qb = hub.subscribe(str(tenant_a["company_id"])), hub.subscribe(str(tenant_b["company_id"]))
    sid = (await client.post("/api/v1/submissions", json=submission_body(), headers=auth(ag))).json()["id"]
    await process_outbox_once(500)
    ev = qa.get_nowait()
    assert ev["type"] == "submission.accepted" and ev["submission_id"] == sid
    assert qb.empty()
    assert (await _outbox_row(sid)).processed_at is not None


async def test_outbox_retry_with_backoff(client, tenant_a, monkeypatch):
    ag = await login(client, tenant_a["agent_email"])
    sid = (await client.post("/api/v1/submissions", json=submission_body(), headers=auth(ag))).json()["id"]

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(hub, "publish", boom)
    await process_outbox_once(500)
    row = await _outbox_row(sid)
    assert row.processed_at is None and row.attempts == 1 and "boom" in row.last_error
    monkeypatch.undo()
    async with SessionLocal() as s:
        r = await s.get(OutboxEvent, row.id)
        r.next_attempt_at = r.created_at
        await s.commit()
    await process_outbox_once(500)
    assert (await _outbox_row(sid)).processed_at is not None


async def test_sse_ticket_and_stream_scoping(client, tenant_a):
    from app.api.v1.events import company_from_ticket, event_stream
    ag = await login(client, tenant_a["agent_email"])
    adm = await login(client, tenant_a["admin_email"])
    assert (await client.post("/api/v1/events/ticket", headers=auth(ag))).status_code == 403
    assert (await client.get("/api/v1/events/submissions?ticket=junk")).status_code == 401
    r = await client.get(f"/api/v1/events/submissions?ticket={adm['access_token']}")
    assert r.status_code == 401  # a normal access token is not a stream ticket
    t = (await client.post("/api/v1/events/ticket", headers=auth(adm))).json()["ticket"]
    cid = company_from_ticket(t)
    assert cid == str(tenant_a["company_id"])
    gen = event_stream(cid, keepalive=0.2)
    assert "retry" in await gen.__anext__()
    hub.publish(cid, {"id": 1, "type": "submission.accepted", "submission_id": "x"})
    frame = await gen.__anext__()
    assert frame.startswith("id: 1\nevent: submission.accepted")
    assert json.loads(frame.split("data: ")[1])["submission_id"] == "x"
    assert (await gen.__anext__()).startswith(": keepalive")
    await gen.aclose()


async def test_dashboard_and_audit(client, tenant_a, tenant_b):
    ag, adm = await login(client, tenant_a["agent_email"]), await login(client, tenant_a["admin_email"])
    b_adm = await login(client, tenant_b["admin_email"])
    await client.post("/api/v1/submissions", json=submission_body(), headers=auth(ag))
    await client.post("/api/v1/branches", headers=auth(adm), json={"name": "Z", "code": "Z1"})
    d = (await client.get("/api/v1/dashboard", headers=auth(adm))).json()
    assert d["total_agents"] == 1 and d["active_branches"] == 2 and d["submissions_today"] == 1
    assert d["pending_review"] == 1 and len(d["recent"]) == 1 and d["trend"][-1]["count"] == 1
    other = (await client.get("/api/v1/dashboard", headers=auth(b_adm))).json()
    assert other["submissions_today"] == 0 and other["recent"] == [] and other["trend"] == []
    logs = (await client.get("/api/v1/audit-logs", headers=auth(adm))).json()
    assert logs["total"] == 1 and logs["items"][0]["action"] == "branch.create"
    assert (await client.get("/api/v1/audit-logs", headers=auth(b_adm))).json()["total"] == 0
    assert (await client.get("/api/v1/dashboard", headers=auth(ag))).status_code == 403
