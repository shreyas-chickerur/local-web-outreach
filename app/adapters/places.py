"""Google Places — look one business up by name.

The only source that reliably returns a business's own website, which is what
answers "do they even have a site?". Yelp returns its own page; OpenStreetMap
usually returns nothing at all for a service business.

Uses the Places API (New): one request returns website, phone, hours, rating,
review count and business status together. The legacy pair of Text Search +
Place Details cost two requests for less.
"""

from __future__ import annotations

import httpx

from app.adapters.directory import DirectoryPlace
from app.adapters.gplaces import PlacesError, _to_place, search
from app.core import config
from app.workbench.match import same_business


class GooglePlacesDirectory:
    """Look one business up by name and return what Google knows about it."""

    name = "google"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None,
                 timeout: float = 20.0) -> None:
        self._api_key = api_key or config.google_places_api_key() or ""
        self._client = client or httpx.Client(timeout=timeout)

    def lookup(self, name: str, location: str) -> DirectoryPlace | None:
        if not self._api_key or not name:
            return None
        try:
            results = search(self._api_key, f"{name} {location}".strip(),
                             client=self._client)
        except PlacesError:
            return None
        if not results:
            return None
        top = results[0]
        # How many results carried this name is the cheapest chain signal there
        # is, and the only one left when the brand's site blocks our reader.
        top_name = (top.get("displayName") or {}).get("text", "")
        nearby = sum(1 for r in results
                     if same_business(top_name, (r.get("displayName") or {}).get("text", "")))
        return _to_place(top, same_name_nearby=nearby)
