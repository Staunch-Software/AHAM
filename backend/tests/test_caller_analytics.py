"""Tests for the Call Master Caller Analytics endpoint."""
from datetime import date
import pytest
from app.services.sankalp import rules as R
from tests.conftest import as_
from tests.test_calling_flow import Flow, OK, clock  # noqa: F401


@pytest.mark.asyncio
async def test_caller_analytics_endpoint(client, tenant_a, clock):
    f = Flow(client, tenant_a)
    caller_id = str(tenant_a["caller1_id"])

    # 1. Check analytics when no calls have been recorded yet
    res = await client.get(
        f"/api/v1/reports/callcentre/caller/{caller_id}?period=custom&date_from=2026-10-20&date_to=2026-10-22",
        headers=await f("master"),
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["caller"]["id"] == caller_id
    assert "daily_limit" in data["caller"]
    assert data["summary"]["total_attempts"] == 0
    assert data["summary"]["connected_calls"] == 0
    assert len(data["slot_distribution"]) == len(R.SLOTS)

    # 2. Record an entry, allocate to caller1, and record a call attempt on 2026-10-21
    e = await f.entry("so1", day="2026-10-20")
    await f.callers("2026-10-21", {"b1": "caller1"})
    await f.run("2026-10-21")
    await f.call("caller1", e["id"], R.CONNECTED, answers=OK)

    # 3. Query analytics for the test range
    res2 = await client.get(
        f"/api/v1/reports/callcentre/caller/{caller_id}?period=custom&date_from=2026-10-20&date_to=2026-10-22",
        headers=await f("master"),
    )
    assert res2.status_code == 200, res2.text
    data2 = res2.json()

    assert data2["summary"]["total_attempts"] == 1
    assert data2["summary"]["connected_calls"] == 1
    assert data2["summary"]["connected_pct"] == 100.0
    assert len(data2["recent_calls"]) == 1
    assert data2["recent_calls"][0]["outcome"] == R.CONNECTED
    assert data2["recent_calls"][0]["slot"] == "10-11"

    # Outcome breakdown check
    connected_breakdown = [o for o in data2["outcome_breakdown"] if o["outcome"] == R.CONNECTED]
    assert len(connected_breakdown) == 1
    assert connected_breakdown[0]["count"] == 1

    # Slot check
    slot_10_11 = [s for s in data2["slot_distribution"] if s["slot"] == "10-11"]
    assert len(slot_10_11) == 1
    assert slot_10_11[0]["attempts"] == 1
    assert slot_10_11[0]["connected"] == 1

    # 4. Check Excel export endpoint
    res_export = await client.get(
        f"/api/v1/reports/callcentre/caller/{caller_id}/export.xlsx?period=custom&date_from=2026-10-20&date_to=2026-10-22",
        headers=await f("master"),
    )
    assert res_export.status_code == 200
    assert res_export.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(res_export.content) > 1000

    # 5. Check Master Team Analytics endpoint
    res_master = await client.get(
        "/api/v1/reports/callcentre/master-analytics?period=custom&date_from=2026-10-20&date_to=2026-10-22",
        headers=await f("master"),
    )
    assert res_master.status_code == 200, res_master.text
    master_data = res_master.json()
    assert master_data["summary"]["total_attempts"] == 1
    assert master_data["summary"]["connected_calls"] == 1
    assert len(master_data["callers"]) >= 1
    # Check that caller1 is present and ranked with 1 attempt
    caller1_entry = [c for c in master_data["callers"] if c["caller_id"] == caller_id][0]
    assert caller1_entry["attempts"] == 1
    assert caller1_entry["connected"] == 1
    assert len(master_data["slot_distribution"]) == len(R.SLOTS)
    assert len(master_data["recent_calls"]) == 1
    assert master_data["recent_calls"][0]["caller_name"] is not None

    # 6. Check Master Team 3-sheet Excel export endpoint
    res_master_export = await client.get(
        "/api/v1/reports/callcentre/master-analytics/export.xlsx?period=custom&date_from=2026-10-20&date_to=2026-10-22",
        headers=await f("master"),
    )
    assert res_master_export.status_code == 200
    assert res_master_export.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(res_master_export.content) > 1000

