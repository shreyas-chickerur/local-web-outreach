"""Yelp Fusion lookup — the directory that actually covers local service businesses.

OpenStreetMap misses service-area businesses (lawn care, plumbing, locksmiths):
they have no mapped storefront. Yelp lists them, with address and phone, which is
what lets those facts reach VERIFIED.

Needs a free API key (`YELP_API_KEY`); without one this source is simply absent
and the pipeline falls back to whatever else it has — it never guesses.
"""

from __future__ import annotations

import httpx

from app.adapters.directory import DirectoryPlace
from app.core.config import yelp_api_key

SEARCH_URL = "https://api.yelp.com/v3/businesses/search"


class YelpSource:
    """Live Yelp Fusion lookup. ``client`` is injectable for tests."""

    name = "yelp"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None,
                 timeout: float = 10.0) -> None:
        self._key = api_key or yelp_api_key()
        self._client = client or httpx.Client(timeout=timeout)

    def lookup(self, name: str, location: str) -> DirectoryPlace | None:
        if not self._key:
            return None
        try:
            resp = self._client.get(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {self._key}"},
                params={"term": name, "location": location, "limit": 1},
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None
        businesses = (data or {}).get("businesses") or []
        return parse_yelp_business(businesses[0]) if businesses else None


def parse_yelp_business(row: dict) -> DirectoryPlace | None:
    """Map one Yelp business to a ``DirectoryPlace`` (pure — unit-testable)."""
    if not row:
        return None
    loc = row.get("location") or {}
    display = [line for line in (loc.get("display_address") or []) if line]
    address = ", ".join(display) or None
    return DirectoryPlace(
        name=row.get("name") or "",
        address=address,
        phone=row.get("display_phone") or row.get("phone") or None,
        website=None,  # Yelp returns its own page, not the business's site
        source_url=row.get("url") or "https://www.yelp.com/",
    )
