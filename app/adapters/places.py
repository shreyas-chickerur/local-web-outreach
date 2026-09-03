"""Places data sources.

A ``PlacesSource`` turns a location (+ optional category) into raw
``BusinessCandidate`` records. Real production data comes from a licensed
provider (Google Places / Outscraper / Apify); ``StubPlacesSource`` is a
deterministic, fixture-backed source so the whole pipeline can be exercised
without network or API keys.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.adapters.directory import DirectoryPlace
from app.core import config


@dataclass(frozen=True)
class BusinessCandidate:
    """One raw business as returned by a places source (pre-qualification)."""

    place_id: str
    name: str
    location: str
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    # The website the *source claims* — unverified, may be social or absent.
    website: str | None = None
    country: str = "US"
    rating: float | None = None
    review_count: int | None = None


class PlacesSource(ABC):
    """Interface every places provider implements."""

    @abstractmethod
    def search(self, location: str, category: str | None = None) -> list[BusinessCandidate]:
        ...


class StubPlacesSource(PlacesSource):
    """Deterministic source backed by an in-memory list (tests, dry runs)."""

    def __init__(self, candidates: list[BusinessCandidate]) -> None:
        self._candidates = candidates

    def search(self, location: str, category: str | None = None) -> list[BusinessCandidate]:
        results = [c for c in self._candidates if location.lower() in c.location.lower()]
        if category:
            results = [c for c in results if (c.category or "").lower() == category.lower()]
        return results


class GooglePlacesSource(PlacesSource):
    """Google Places Text Search adapter (used in production with an API key)."""

    BASE_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def __init__(self, api_key: str, client: httpx.Client | None = None,
                 fetch_details: bool = True) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=15.0)
        self._fetch_details = fetch_details

    def search(self, location: str, category: str | None = None) -> list[BusinessCandidate]:
        query = f"{category} in {location}" if category else f"businesses in {location}"
        resp = self._client.get(self.BASE_URL, params={"query": query, "key": self._api_key})
        resp.raise_for_status()
        payload = resp.json()
        out: list[BusinessCandidate] = []
        for r in payload.get("results", []):
            place_id = r["place_id"]
            # Text Search does NOT return website or phone — they come only from
            # Place Details. Without this call every business looks like it has
            # no website (so the outreach email would say so, wrongly) and has no
            # phone for a second source to corroborate.
            details = self._details(place_id) if self._fetch_details else {}
            out.append(
                BusinessCandidate(
                    place_id=place_id,
                    name=r.get("name", ""),
                    location=location,
                    category=category,
                    address=r.get("formatted_address"),
                    phone=details.get("formatted_phone_number"),
                    website=details.get("website"),
                    rating=r.get("rating"),
                    review_count=r.get("user_ratings_total"),
                )
            )
        return out

    def _details(self, place_id: str) -> dict:
        """Fetch the contact fields Text Search omits. A failure degrades to an
        empty dict rather than losing the candidate."""
        try:
            resp = self._client.get(
                self.DETAILS_URL,
                params={"place_id": place_id,
                        "fields": "formatted_phone_number,website",
                        "key": self._api_key},
            )
            resp.raise_for_status()
            return resp.json().get("result") or {}
        except (httpx.HTTPError, ValueError):
            return {}


def get_places_source(client: httpx.Client | None = None) -> PlacesSource:
    """Return the configured live places source.

    Raises a clear, actionable error if the required credential is missing —
    tests use ``StubPlacesSource`` directly and never hit this.
    """
    provider = config.places_provider()
    if provider == "google":
        key = config.google_places_api_key()
        if not key:
            raise RuntimeError(
                "GOOGLE_PLACES_API_KEY is not set. Copy .env.example to .env and add your "
                "key (or run `python -m app.cli demo` to try the pipeline with no key)."
            )
        return GooglePlacesSource(api_key=key, client=client)
    raise RuntimeError(f"Unknown PLACES_PROVIDER={provider!r} (supported: 'google').")


class GooglePlacesDirectory:
    """Look ONE business up by name — the lookup shape the workbench needs.

    ``GooglePlacesSource`` searches a category across a city; this searches a
    specific business and returns the record for it. Crucially it returns the
    business's real website, which Yelp and OpenStreetMap usually do not, so it
    is the source that answers "do they even have a site?".
    """

    name = "google"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None,
                 timeout: float = 15.0) -> None:
        self._api_key = api_key or config.google_places_api_key()
        self._client = client or httpx.Client(timeout=timeout)

    def lookup(self, name: str, location: str) -> DirectoryPlace | None:
        from app.adapters.directory import DirectoryPlace

        if not self._api_key or not name:
            return None
        query = f"{name} {location}".strip()
        try:
            resp = self._client.get(
                GooglePlacesSource.BASE_URL,
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
                    GooglePlacesSource.DETAILS_URL,
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
