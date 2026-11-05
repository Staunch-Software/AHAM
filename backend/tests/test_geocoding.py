import httpx
import pytest

from app.core.config import Settings
from app.services import geocoding
from app.services.geocoding import GoogleGeocoder, NominatimGeocoder, google_name, nominatim_name
from app.workers.geocode import MAX_ATTEMPTS, geocode_once
from tests.conftest import as_, make_entry, upload_photo

NOMINATIM_SAMPLE = {
    "display_name": "Gandhi Road, Nellore, Spsr Nellore, Andhra Pradesh, 524001, India",
    "address": {"road": "Gandhi Road", "suburb": "Stonehousepeta", "city": "Nellore", "state": "Andhra Pradesh", "country": "India"},
}


def test_name_parsing():
    assert nominatim_name(NOMINATIM_SAMPLE) == "Gandhi Road, Stonehousepeta, Nellore, Andhra Pradesh"
    assert nominatim_name({"display_name": "Somewhere, India", "address": {}}) == "Somewhere, India"
    assert nominatim_name({}) is None
    assert google_name({"status": "OK", "results": [{"formatted_address": "12 Gandhi Rd, Nellore, India"}]}) == "12 Gandhi Rd, Nellore, India"
    assert google_name({"status": "ZERO_RESULTS", "results": []}) is None


def test_google_prefers_the_most_specific_real_address():
    results = [
        {"types": ["plus_code"], "formatted_address": "5C6M+X8 Nellore, Andhra Pradesh, India"},
        {"types": ["locality", "political"], "formatted_address": "Nellore, Andhra Pradesh, India"},
        {"types": ["route"], "formatted_address": "VRC Rd, Vaddipalem, Nellore, Andhra Pradesh 524004, India"},
        {"types": ["street_address"], "formatted_address": "12-3-4, VRC Rd, Vaddipalem, Nellore, Andhra Pradesh 524004, India"},
        {"types": ["premise"], "formatted_address": "Acme Towers, VRC Rd, Nellore, India"},
    ]
    assert google_name({"status": "OK", "results": results}).startswith("12-3-4, VRC Rd")  # street address beats all
    assert google_name({"status": "OK", "results": results[:3]}).startswith("VRC Rd")  # route beats area and plus code
    assert google_name({"status": "OK", "results": results[:2]}) == "Nellore, Andhra Pradesh, India"  # not the plus code
    assert google_name({"status": "OK", "results": results[:1]}) == "5C6M+X8 Nellore, Andhra Pradesh, India"  # only option


def test_google_skips_street_addresses_that_start_with_a_plus_code():
    # real response shape seen for Chennai: the first candidate is typed street_address but written with a plus code
    results = [
        {"types": ["premise", "street_address"], "formatted_address": "267F+X4V, Gotha Medu Housing Board, Saidapet, Chennai, Tamil Nadu 600015, India"},
        {"types": ["establishment", "lodging", "point_of_interest"], "formatted_address": "BLOCK-B, Little Mount, Saidapet, Chennai, Tamil Nadu 600015, India"},
        {"types": ["street_address"], "formatted_address": "16/183, Anna Salai, Gotha Medu Housing Board, Saidapet, Chennai, Tamil Nadu 600015, India"},
    ]
    assert google_name({"status": "OK", "results": results}).startswith("16/183, Anna Salai")
    assert google_name({"status": "OK", "results": results[:2]}).startswith("BLOCK-B, Little Mount")
    assert google_name({"status": "OK", "results": results[:1]}).startswith("267F+X4V")  # still better than no name


async def test_nominatim_client_identifies_itself_and_caches():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json=NOMINATIM_SAMPLE)

    g = NominatimGeocoder("FieldSync/test (qa@x.io)", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), min_interval=0)
    a = await g.reverse(14.44261, 79.98651)
    b = await g.reverse(14.44263, 79.98649)  # ~2 m away: same rounded key -> served from cache
    assert a == b == "Gandhi Road, Stonehousepeta, Nellore, Andhra Pradesh"
    assert len(seen) == 1
    assert seen[0].headers["user-agent"] == "FieldSync/test (qa@x.io)" and seen[0].url.params["lat"] == "14.442610"
    await g.reverse(16.5, 80.6)
    assert len(seen) == 2


async def test_google_client_parses_response():
    def handler(req):
        assert req.url.params["key"] == "k" and req.url.params["latlng"].startswith("14.4426")
        return httpx.Response(200, json={"status": "OK", "results": [{"formatted_address": "Nellore, AP, India"}]})

    g = GoogleGeocoder("k", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await g.reverse(14.4426, 79.9865) == "Nellore, AP, India"


async def test_google_refusal_is_reported_with_the_reason():
    def handler(req):
        return httpx.Response(200, json={"status": "REQUEST_DENIED", "error_message": "This IP, site or mobile application is not authorized"})

    g = GoogleGeocoder("k", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(RuntimeError, match="REQUEST_DENIED: This IP, site or mobile application"):
        await g.reverse(14.4426, 79.9865)

    zero = GoogleGeocoder("k", client=httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"status": "ZERO_RESULTS", "results": []}))))
    assert await zero.reverse(0.0, 0.0) is None  # an empty answer is not an error


def test_logs_never_contain_api_keys(capsys):
    import json
    import logging

    from app.core.logging import configure_logging

    root = logging.getLogger()
    saved = (root.handlers[:], root.level, logging.getLogger("httpx").level, logging.getLogger("httpcore").level)
    try:
        _check_logs_never_contain_api_keys(capsys, json, logging, configure_logging)
    finally:  # leave the process-wide logging exactly as other tests expect it
        root.handlers[:], root.level = saved[0], saved[1]
        logging.getLogger("httpx").setLevel(saved[2])
        logging.getLogger("httpcore").setLevel(saved[3])


def _check_logs_never_contain_api_keys(capsys, json, logging, configure_logging):
    configure_logging()
    url ="https://maps.googleapis.com/maps/api/geocode/json?latlng=1%2C2&key=AIzaSECRETSECRETSECRET&language=en"
    log = logging.getLogger("fieldsync.test")
    log.warning("plain %s", url)
    log.warning("with extra", extra={"error": f"Client error '403' for url '{url}'"})
    try:
        raise httpx.HTTPStatusError(f"Client error for url '{url}'", request=httpx.Request("GET", url), response=httpx.Response(403))
    except httpx.HTTPStatusError:
        log.exception("failed")
    logging.getLogger("httpx").info("HTTP Request: GET %s", url)  # the library's own INFO line is silenced

    out = capsys.readouterr().out
    assert "AIzaSECRET" not in out
    lines = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert [x["message"] for x in lines][:1] == ["plain https://maps.googleapis.com/maps/api/geocode/json?latlng=1%2C2&key=REDACTED&language=en"]
    assert not any(x.get("name") == "httpx" for x in lines)
    assert any("key=REDACTED" in x.get("exc_info", "") for x in lines)


class FakeGeo:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, 0

    async def reverse(self, lat, lon):
        self.calls += 1
        if self.fail:
            raise httpx.ConnectError("offline")
        return f"Place {lat:.2f},{lon:.2f}"


async def test_worker_fills_names_and_api_shows_them(client, tenant_a, monkeypatch):
    so, bm = await as_(client, tenant_a, "so1"), await as_(client, tenant_a, "bm1")
    pid = await upload_photo(client, so, latitude=14.4426, longitude=79.9865, accuracy_m=5, location_status="obtained")
    eid = (await make_entry(client, so, photo_ids=[pid]))["id"]

    # lookups are disabled in tests -> the API says so instead of "pending forever"
    d = (await client.get(f"/api/v1/entries/{eid}", headers=bm)).json()
    assert d["location"]["place_status"] == "disabled"

    geo = FakeGeo()
    await geocode_once(geo, batch=1000)
    monkeypatch.setattr(geocoding, "get_settings", lambda: Settings(geocoder="nominatim", geocoder_user_agent="t (a@b.c)"))
    d = (await client.get(f"/api/v1/entries/{eid}", headers=bm)).json()
    assert d["location"]["place_name"] == "Place 16.50,80.60" and d["location"]["place_status"] == "done"
    assert d["location"]["latitude"] == 16.5  # coordinates untouched
    assert d["photos"][0]["place_name"] == "Place 14.44,79.99" and d["photos"][0]["place_status"] == "done"
    before = geo.calls
    await geocode_once(geo, batch=1000)
    assert geo.calls == before  # done rows are not looked up again


async def test_worker_retries_then_marks_failed_and_skips_rows_without_coordinates(client, tenant_a, monkeypatch):
    so, bm = await as_(client, tenant_a, "so1"), await as_(client, tenant_a, "bm1")
    nocoord = (await make_entry(client, so, location={"status": "timeout"}))["id"]
    withcoord = (await make_entry(client, so))["id"]
    monkeypatch.setattr(geocoding, "get_settings", lambda: Settings(geocoder="nominatim", geocoder_user_agent="t (a@b.c)"))
    geo = FakeGeo(fail=True)
    for i in range(MAX_ATTEMPTS):
        await geocode_once(geo, batch=1000)
        d = (await client.get(f"/api/v1/entries/{withcoord}", headers=bm)).json()
        assert d["location"]["place_status"] == ("failed" if i == MAX_ATTEMPTS - 1 else "pending")
    assert d["location"]["place_name"] is None and d["location"]["latitude"] == 16.5
    n = (await client.get(f"/api/v1/entries/{nocoord}", headers=bm)).json()
    assert n["location"]["latitude"] is None and n["location"]["place_name"] is None


def test_geocoder_settings_validation():
    with pytest.raises(ValueError):
        Settings(_env_file=None, geocoder="google")  # key required
    with pytest.raises(ValueError):
        Settings(_env_file=None, geocoder="bogus")
    with pytest.raises(ValueError):  # production + public OSM needs a real contact in the user agent
        Settings(_env_file=None, app_env="production", jwt_secret="a" * 40, file_url_secret="b" * 40, geocoder="nominatim")
    Settings(_env_file=None, app_env="production", jwt_secret="a" * 40, file_url_secret="b" * 40, geocoder="nominatim",
             geocoder_user_agent="FieldSync/1.0 (ops@acme.com)")
    Settings(_env_file=None, geocoder="google", google_maps_api_key="k")


async def test_regeocode_requeues_rows_with_coordinates(client, tenant_a):
    from sqlalchemy import select
    from app.core.db import SessionLocal
    from app.models import SankalpEntry
    from app.regeocode import main as regeocode
    so = await as_(client, tenant_a, "so1")
    eid = (await make_entry(client, so))["id"]
    await geocode_once(FakeGeo(), batch=1000)
    async with SessionLocal() as s:
        row = (await s.execute(select(SankalpEntry).where(SankalpEntry.id == eid))).scalar_one()
        assert row.place_status == "done"
    await regeocode()
    async with SessionLocal() as s:
        row = (await s.execute(select(SankalpEntry).where(SankalpEntry.id == eid))).scalar_one()
        assert row.place_status == "pending" and row.place_name  # old name stays until replaced
    await geocode_once(FakeGeo(), batch=1000)