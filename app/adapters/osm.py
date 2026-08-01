"""OpenStreetMap (Nominatim) lookup — the second independent source.

Why OSM: a fact only becomes VERIFIED with **two independent** sources, and for a
business with no website the Google Places record is the only one we had, so
nothing could ever corroborate. OSM is community-maintained, free, needs no API
key, and is genuinely independent of Google — which is exactly what the
corroboration rule requires.

Nominatim's usage policy is respected here: an identifying User-Agent, at most
one request per second, and no bulk/heavy querying.
"""

from __future__ import annotations

import threading
import time

import httpx

from app.adapters.directory import DirectoryPlace

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "local-web-outreach/0.1 (contact: friscooperator@gmail.com)"
MIN_INTERVAL_S = 1.1  # Nominatim asks for <= 1 request/second


class NominatimSource:
    """Live Nominatim lookup, rate-limited to honour the usage policy."""

    name = "openstreetmap"

    _lock = threading.Lock()
    _last_call = 0.0

    def __init__(self, client: httpx.Client | None = None, timeout: float = 10.0) -> None:
        self._client = client or httpx.Client(
            timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        )

    def _throttle(self) -> None:
        with NominatimSource._lock:
            wait = MIN_INTERVAL_S - (time.monotonic() - NominatimSource._last_call)
            if wait > 0:
                time.sleep(wait)
            NominatimSource._last_call = time.monotonic()

    def lookup(self, name: str, location: str) -> DirectoryPlace | None:
        self._throttle()
        params = {
            "q": f"{name} {location}".strip(),
            "format": "jsonv2",
            "addressdetails": "1",
            "extratags": "1",
            "limit": "1",
        }
        try:
            resp = self._client.get(NOMINATIM_URL, params=params)
            resp.raise_for_status()
            rows = resp.json()
        except (httpx.HTTPError, ValueError):
            return None
        if not rows:
            return None
        return parse_nominatim_row(rows[0], fallback_name=name)


def _format_address(addr: dict) -> str | None:
    """Build a street address from Nominatim's address components."""
    house, road = addr.get("house_number"), addr.get("road")
    street = f"{house} {road}" if house and road else road
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb")
    parts = [p for p in (street, city, addr.get("state"), addr.get("postcode")) if p]
    return ", ".join(parts) if street and city else None


def parse_nominatim_row(row: dict, *, fallback_name: str = "") -> DirectoryPlace | None:
    """Map one Nominatim result to a ``DirectoryPlace`` (pure — unit-testable)."""
    extra = row.get("extratags") or {}
    osm_type, osm_id = row.get("osm_type"), row.get("osm_id")
    return DirectoryPlace(
        name=row.get("name") or fallback_name,
        address=_format_address(row.get("address") or {}),
        phone=extra.get("phone") or extra.get("contact:phone"),
        website=extra.get("website") or extra.get("contact:website"),
        source_url=(f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
                    if osm_type and osm_id else "https://www.openstreetmap.org/"),
    )
