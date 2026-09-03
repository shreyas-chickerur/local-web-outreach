"""Google Places — look one business up by name.

The only source that reliably returns a business's own website, which is what
answers "do they even have a site?". Yelp returns its own page; OpenStreetMap
usually returns nothing at all for a service business.

Two calls are needed: Text Search finds the place, but returns neither website
nor phone — those come only from Place Details. Reading them off the search
result (as v1 did) makes every business look like it has no website.
"""

from __future__ import annotations

import httpx

from app.adapters.directory import DirectoryPlace
from app.core import config

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class GooglePlacesDirectory:
    """Look one business up by name and return what Google knows about it."""

    name = "google"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None,
                 timeout: float = 15.0) -> None:
        self._api_key = api_key or config.google_places_api_key()
        self._client = client or httpx.Client(timeout=timeout)

    def lookup(self, name: str, location: str) -> DirectoryPlace | None:
        if not self._api_key or not name:
            return None
        query = f"{name} {location}".strip()
        try:
            resp = self._client.get(
                TEXT_SEARCH_URL,
                params={"query": query, "key": self._api_key},
            )
            resp.raise_for_status()
            results = resp.json().get("results") or []
        except (httpx.HTTPError, ValueError):
            return None
        if not results:
            return None

        top = results[0]
        place_id = top.get("place_id", "")
        details: dict = {}
        if place_id:
            try:
                d = self._client.get(
                    DETAILS_URL,
                    params={"place_id": place_id,
                            "fields": "formatted_phone_number,website",
                            "key": self._api_key},
                )
                d.raise_for_status()
                details = d.json().get("result") or {}
            except (httpx.HTTPError, ValueError):
                details = {}

        rating = top.get("rating")
        return DirectoryPlace(
            name=top.get("name", ""),
            address=top.get("formatted_address"),
            phone=details.get("formatted_phone_number"),
            website=details.get("website"),
            source_url=(f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                        if place_id else "https://www.google.com/maps"),
            rating=float(rating) if rating is not None else None,
            review_count=top.get("user_ratings_total"),
        )
