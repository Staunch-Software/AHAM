"""Making Sankalp entries (section 4): identity from the roster, device time kept, idempotency, validation, photos."""
import asyncio
from datetime import datetime, timedelta, timezone

from tests.conftest import as_, entry_body, make_entry, upload_photo


async def _detail(client, headers, eid):
    r = await client.get(f"/api/v1/entries/{eid}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_entry_takes_identity_from_roster_and_id_from_device_time(client, tenant_a):
    so = await as_(client, tenant_a, "so1")
    body = entry_body(branch_id=str(tenant_a["b3"]), emp_code="SOMEONE-ELSE")  # extra fields are ignored
    r = await client.post("/api/v1/entries", json=body, headers=so)
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["entry_code"] == f"{tenant_a['so1_code']}-20261015-090706"  # truncated, not rounded
    assert rec["entry_date"] == "2026-10-15" and rec["count_date"] == "2026-10-15"
    d = await _detail(client, so, rec["id"])
    assert d["branch_name"] == "Branch One" and d["region_name"] == "Region One"
    assert d["so_employee_code"] == tenant_a["so1_code"] and d["phone"] == "9876543210"
    assert d["phone_raw"] == "+91 98765 43210" and d["call_group"] == "lead" and d["rag"] == "PENDING"
    assert d["history"][0]["kind"] == "created"


async def test_offline_entry_keeps_the_time_and_place_of_submit(client, tenant_a):
    """Made offline two days ago, synced now: entry time, date, ID and GPS are those of the Submit press."""
    so = await as_(client, tenant_a, "so1")
    made = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=2, hours=3)
    fix = made + timedelta(seconds=2)
    rec = await make_entry(client, so, submitted_at_device=made.isoformat(),
                           location={"latitude": 14.44, "longitude": 79.98, "accuracy_m": 8,
                                     "fix_at_device": fix.isoformat(), "status": "obtained"})
    d = await _detail(client, so, rec["id"])
    assert datetime.fromisoformat(d["submitted_at_device"]) == made
    assert datetime.fromisoformat(d["received_at_server"]) - made > timedelta(days=2)
    ist = made.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert rec["entry_code"].endswith(f"-{ist:%Y%m%d}-{ist:%H%M%S}") and d["entry_date"] == f"{ist:%Y-%m-%d}"
    assert d["location"]["latitude"] == 14.44 and datetime.fromisoformat(d["location"]["fix_at_device"]) == fix
    assert d["history"][0]["detail"]["synced_after_s"] > 2 * 86400 and d["device_time_suspect"] is False


async def test_device_time_in_the_future_is_flagged(client, tenant_a):
    so = await as_(client, tenant_a, "so1")
    ahead = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    d = await _detail(client, so, (await make_entry(client, so, submitted_at_device=ahead))["id"])
    assert d["device_time_suspect"] is True


async def test_sunday_and_holiday_entries_count_on_next_working_day(client, tenant_a):
    so, mon = await as_(client, tenant_a, "so1"), await as_(client, tenant_a, "monitor")
    assert (await client.post("/api/v1/holidays", headers=mon, json={"day": "2026-10-19", "name": "Test"})).status_code == 201
    rec = await make_entry(client, so, submitted_at_device="2026-10-18T11:00:00+05:30")  # Sunday
    assert rec["entry_date"] == "2026-10-18" and rec["count_date"] == "2026-10-20"
    assert rec["entry_code"].endswith("-20261018-110000")  # the Entry ID keeps the real time


async def test_replay_is_idempotent_and_key_reuse_conflicts(client, tenant_a):
    so = await as_(client, tenant_a, "so1")
    body = entry_body(submitted_at_device="2026-10-16T10:00:00+05:30")
    first = await client.post("/api/v1/entries", json=body, headers=so)
    again = await client.post("/api/v1/entries", json=body, headers=so)
    assert first.status_code == 201 and again.status_code == 201
    assert again.json()["id"] == first.json()["id"] and again.json()["duplicate"] is True
    changed = await client.post("/api/v1/entries", json={**body, "person_name": "Other"}, headers=so)
    assert changed.status_code == 409 and changed.json()["detail"]["code"] == "idempotency_conflict"


async def test_concurrent_retries_make_one_entry(client, tenant_a):
    so = await as_(client, tenant_a, "so1")
    body = entry_body(submitted_at_device="2026-10-16T10:30:00+05:30")
    rs = await asyncio.gather(*[client.post("/api/v1/entries", json=body, headers=so) for _ in range(5)])
    assert {r.status_code for r in rs} == {201} and len({r.json()["id"] for r in rs}) == 1


async def test_same_second_entries_get_a_suffix(client, tenant_a):
    so = await as_(client, tenant_a, "so1")
    t = "2026-10-16T11:00:00+05:30"
    a = await make_entry(client, so, submitted_at_device=t)
    b = await make_entry(client, so, submitted_at_device=t, phone="9123456780")
    assert b["entry_code"] == a["entry_code"] + "-2"


async def test_validation(client, tenant_a):
    so = await as_(client, tenant_a, "so1")

    async def errors(**over):
        r = await client.post("/api/v1/entries", json=entry_body(**over), headers=so)
        assert r.status_code == 422, r.text
        d = r.json()["detail"]
        return {e["field"] for e in d["errors"]} if isinstance(d, dict) else {".".join(map(str, e["loc"][1:])) for e in d}

    assert await errors(phone="12345") == {"phone"}
    assert await errors(phone="+91 58765 43210") == {"phone"}  # must start with 6-9
    assert await errors(person_name="  ", description="") == {"person_name", "description"}
    assert await errors(category="contact_point") == {"cp_subtype_id"}  # CP needs its sub-type
    assert "category" in await errors(category="Dealer")
    assert "submitted_at_device" in await errors(submitted_at_device="2026-10-15T09:07:06")  # no offset


async def test_contact_point_with_subtype_and_dsa_group(client, tenant_a):
    so = await as_(client, tenant_a, "so1")
    subtypes = (await client.get("/api/v1/cp-subtypes/active", headers=so)).json()
    assert [s["label"] for s in subtypes][:2] == ["Sand / Gravel / Brick Shop", "Other Hardware Shop"]
    rec = await make_entry(client, so, category="contact_point", cp_subtype_id=subtypes[0]["id"])
    d = await _detail(client, so, rec["id"])
    assert d["category_label"] == "Contact Point" and d["cp_subtype_label"] == "Sand / Gravel / Brick Shop"
    assert d["call_group"] == "dsa_cp"
    wrong = await client.post("/api/v1/entries", json=entry_body(category="lead", cp_subtype_id=subtypes[0]["id"]), headers=so)
    assert wrong.status_code == 422
    existing = await make_entry(client, so, category="existing_customer")
    assert (await _detail(client, so, existing["id"]))["call_group"] == "none"


async def test_photos_attach_once_and_only_own(client, tenant_a):
    so1, so2, bm = await as_(client, tenant_a, "so1"), await as_(client, tenant_a, "so2"), await as_(client, tenant_a, "bm1")
    pid = await upload_photo(client, so1, latitude=16.51, longitude=80.61, accuracy_m=4, location_status="obtained",
                             photo_captured_at_device="2026-10-15T09:05:00+05:30")
    rec = await make_entry(client, so1, photo_ids=[pid])
    d = await _detail(client, bm, rec["id"])
    assert d["photo_count"] == 1 and d["photos"][0]["latitude"] == 16.51
    assert d["photos"][0]["photo_captured_at_device"].startswith("2026-10-15T03:35:00")
    assert (await client.get(d["photos"][0]["thumb_url"])).status_code == 200
    reuse = await client.post("/api/v1/entries", json=entry_body(photo_ids=[pid]), headers=so1)
    assert reuse.status_code == 422  # already attached
    theirs = await client.post("/api/v1/entries", json=entry_body(photo_ids=[pid]), headers=so2)
    assert theirs.status_code == 422
    # photo links: BM of the branch may view, BM of another branch may not
    bm3 = await as_(client, tenant_a, "bm3")
    assert (await client.get(f"/api/v1/photos/{pid}/url", headers=bm)).status_code == 200
    assert (await client.get(f"/api/v1/photos/{pid}/url", headers=bm3)).status_code == 404


async def test_so_without_branch_cannot_submit(client, tenant_a):
    from app.core.db import SessionLocal
    from app.models import User

    async with SessionLocal() as s:
        u = await s.get(User, tenant_a["so3_id"])
        u.branch_id = None
        await s.commit()
    r = await client.post("/api/v1/entries", json=entry_body(), headers=await as_(client, tenant_a, "so3"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "no_branch"


async def test_my_summary_counts_today_against_targets(client, tenant_a):
    so = await as_(client, tenant_a, "so2")
    now = datetime.now(timezone.utc).isoformat()
    for cat, phone in (("lead", "9000000001"), ("prospect", "9000000002"), ("dsa_connector", "9000000003")):
        await make_entry(client, so, category=cat, phone=phone, submitted_at_device=now)
    m = (await client.get("/api/v1/me/summary", headers=so)).json()
    if datetime.now(timezone(timedelta(hours=5, minutes=30))).weekday() != 6:  # Sunday entries count tomorrow
        assert m["entries_today"] == 3 and m["lead_prospect_today"] == 2
    assert m["entry_target"] == 10 and m["lead_target"] == 5


async def test_list_filters(client, tenant_a):
    so, mon = await as_(client, tenant_a, "so1"), await as_(client, tenant_a, "monitor")
    await make_entry(client, so, person_name="Filterable Person", phone="9111111111", category="prospect")
    r = (await client.get("/api/v1/entries?q=Filterable", headers=mon)).json()
    assert r["total"] == 1 and r["items"][0]["category_label"] == "Prospect"
    assert (await client.get("/api/v1/entries?q=91111", headers=mon)).json()["total"] == 1
    assert (await client.get("/api/v1/entries?category=prospect&q=Filterable", headers=mon)).json()["total"] == 1
    assert (await client.get("/api/v1/entries?rag=PENDING&q=Filterable", headers=mon)).json()["total"] == 1
    assert (await client.get("/api/v1/entries?status=Pending&q=Filterable", headers=mon)).json()["total"] == 1
    assert (await client.get(f"/api/v1/entries?branch_id={tenant_a['b2']}&q=Filterable", headers=mon)).json()["total"] == 0
