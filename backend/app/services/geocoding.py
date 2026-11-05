"""Reverse geocoding: coordinates -> a short, human-readable place name.

The coordinates themselves are the evidence and are never changed; the name is a convenience shown next to them.
Providers: Nominatim (OpenStreetMap, free, strict usage policy: <= 1 request/second, identify the app, cache), Google
Geocoding API (key required). Lookups run in a background worker, never inside a request.
"""
import asyncio
import logging
import re
import time
from collections import OrderedDict
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import get_settings

log = logging.getLogger("fieldsync.geocoding")


class Geocoder(Protocol):
    async def reverse(self, lat: float, lon: float) -> str | None: ...


def _join(*parts: str | None) -> str | None:
    seen, out = set(), []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return ", ".join(out) or None


def nominatim_name(data: dict) -> str | None:
    """'Road, Locality, City, State' from Nominatim's address parts; falls back to its display_name."""
    a = data.get("address") or {}
    road = a.get("road") or a.get("pedestrian") or a.get("footway") or a.get("amenity") or a.get("building")
    area = a.get("neighbourhood") or a.get("suburb") or a.get("hamlet") or a.get("quarter")
    city = a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or a.get("county")
    name = _join(road, area, city, a.get("state"))
    return name or data.get("display_name") or None


# Google returns several candidates for one point (building, street, area, plus code ...). Prefer the most specific
# real address; never a bare "plus code" like "5C6M+X8".
_GOOGLE_PREFERRED = ["street_address", "premise", "subpremise", "establishment", "point_of_interest", "route"]
# Google sometimes tags a result `street_address`/`premise` yet writes it as "267F+X4V, Housing Board, Chennai":
# an open location code in front of a vague area name. A readable address beats that.
_LEADING_PLUS_CODE = re.compile(r"^[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}\b")


def _google_rank(result: dict) -> int:
    types = result.get("types") or []
    if "plus_code" in types:
        return 99
    if _LEADING_PLUS_CODE.match(result.get("formatted_address") or ""):
        return 98
    for i, t in enumerate(_GOOGLE_PREFERRED):
        if t in types:
            return i
    return 50  # neighbourhood / locality / etc.: usable, but less exact


def google_name(data: dict) -> str | None:
    if data.get("status") != "OK" or not data.get("results"):
        return None
    best = min(data["results"], key=_google_rank)  # stable: ties keep Google's own order
    return best.get("formatted_address") or None


class NominatimGeocoder:
    URL = "https://nominatim.openstreetmap.org/reverse"

    def __init__(self, user_agent: str, client: httpx.AsyncClient | None = None, min_interval: float = 1.1):
        self._client = client or httpx.AsyncClient(timeout=8.0)
        self._headers = {"User-Agent": user_agent, "Accept-Language": "en"}
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last = 0.0
        self._cache: OrderedDict[tuple[float, float], str | None] = OrderedDict()

    async def reverse(self, lat: float, lon: float) -> str | None:
        key = (round(lat, 4), round(lon, 4))  # ~11 m: photos taken at one spot share one lookup
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        async with self._lock:  # one request at a time, spaced out, per the usage policy
            wait = self._min_interval - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                r = await self._client.get(
                    self.URL, headers=self._headers,
                    params={"format": "jsonv2", "lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "zoom": 18, "addressdetails": 1},
                )
                r.raise_for_status()
                name = nominatim_name(r.json())
            finally:
                self._last = time.monotonic()
        self._cache[key] = name
        if len(self._cache) > 5000:
            self._cache.popitem(last=False)
        return name


class GoogleGeocoder:
    URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        self._key = api_key
        self._client = client or httpx.AsyncClient(timeout=8.0)

    async def reverse(self, lat: float, lon: float) -> str | None:
        r = await self._client.get(self.URL, params={"latlng": f"{lat:.6f},{lon:.6f}", "key": self._key, "language": "en"})
        r.raise_for_status()
        data = r.json()
        # Google answers HTTP 200 even when it refuses the key; say why instead of failing silently.
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            raise RuntimeError(f"Google Geocoding {data.get('status')}: {str(data.get('error_message') or '')[:160]}")
        return google_name(data)


@lru_cache
def get_geocoder() -> Geocoder | None:
    s = get_settings()
    if s.geocoder == "nominatim":
        return NominatimGeocoder(s.geocoder_user_agent)
    if s.geocoder == "google":
        return GoogleGeocoder(s.google_maps_api_key)
    return None


def place_status_for_api(status: str) -> str:
    """What the API reports: 'disabled' when no geocoder is configured (so the UI doesn't wait forever)."""
    return "disabled" if get_settings().geocoder == "none" else status
