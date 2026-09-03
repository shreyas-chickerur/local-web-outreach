"""Google Places API (New) — one request per search, not two.

The legacy Text Search returned neither website nor phone, so every business
needed a second Place Details call to answer "do they even have a site?". The
new API takes a field mask and returns website, phone, hours, rating, review
count, business status and a description in the same response. That is the
difference between one request per category and one per business, which is what
makes a page of prospects affordable to load.
"""

from __future__ import annotations

import httpx

from app.adapters.directory import DirectoryPlace

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Ask for exactly what the brief and the prospect score use. Field masks are
# billed by tier, so an unused field is money spent for nothing.
FIELDS = (
    "places.id,places.displayName,places.formattedAddress,places.rating,"
    "places.userRatingCount,places.websiteUri,places.nationalPhoneNumber,"
    "places.regularOpeningHours,places.businessStatus,places.googleMapsUri,"
    "places.editorialSummary,places.primaryTypeDisplayName,places.location,"
    "places.reviews,places.photos,places.priceLevel"
)


class PlacesError(RuntimeError):
    """The API refused us, with the reason it gave.

    Worth surfacing rather than swallowing: the usual cause is that Places API
    (New) is not enabled on the key, which no amount of retrying will fix.
    """


def _to_place(raw: dict, same_name_nearby: int = 1) -> DirectoryPlace:
    hours = ((raw.get("regularOpeningHours") or {}).get("weekdayDescriptions") or [])
    # Their customers' own words, attributed. The most credible copy on any
    # small business site is the part the business did not write.
    reviews = tuple(
        {"rating": r.get("rating"),
         "author": (r.get("authorAttribution") or {}).get("displayName", ""),
         "text": (r.get("text") or {}).get("text", "")}
        for r in (raw.get("reviews") or [])
        if (r.get("text") or {}).get("text"))
    # Photo resource names, not URLs: fetching one needs the API key, so the
    # page asks our own server for it and the key never leaves this machine.
    photos = tuple(p["name"] for p in (raw.get("photos") or []) if p.get("name"))
    location = raw.get("location") or {}
    rating = raw.get("rating")
    return DirectoryPlace(
        name=(raw.get("displayName") or {}).get("text", ""),
        address=raw.get("formattedAddress"),
        phone=raw.get("nationalPhoneNumber"),
        website=raw.get("websiteUri"),
        source_url=raw.get("googleMapsUri") or "https://www.google.com/maps",
        rating=float(rating) if rating is not None else None,
        review_count=raw.get("userRatingCount"),
        categories=((raw.get("primaryTypeDisplayName") or {}).get("text", ""),)
        if raw.get("primaryTypeDisplayName") else (),
        hours=tuple(str(h) for h in hours[:7]),
        same_name_nearby=same_name_nearby,
        business_status=raw.get("businessStatus"),
        summary=(raw.get("editorialSummary") or {}).get("text"),
        latitude=location.get("latitude"),
        longitude=location.get("longitude"),
        reviews=reviews,
        photo_refs=photos[:12],
        price_level=raw.get("priceLevel"),
    )


def search(api_key: str, text: str, *, latitude: float | None = None,
           longitude: float | None = None, radius_m: float = 15000.0,
           limit: int = 20, client: httpx.Client | None = None) -> list[dict]:
    """Raw results for a query, biased to a point when one is known."""
    if not api_key or not text.strip():
        return []
    body: dict = {"textQuery": text, "maxResultCount": min(limit, 20)}
    if latitude is not None and longitude is not None:
        body["locationBias"] = {"circle": {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius": radius_m}}
    http = client or httpx.Client(timeout=20.0)
    try:
        resp = http.post(SEARCH_URL, json=body, headers={
            "X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELDS})
    except httpx.HTTPError as exc:
        raise PlacesError(f"could not reach Google Places: {exc}") from exc
    if resp.status_code != 200:
        detail = ""
        try:
            detail = (resp.json().get("error") or {}).get("message", "")
        except ValueError:
            detail = resp.text[:200]
        raise PlacesError(f"Google Places returned {resp.status_code}: {detail}")
    try:
        return list(resp.json().get("places") or [])
    except ValueError as exc:
        raise PlacesError("Google Places returned something that is not JSON") from exc


def places(api_key: str, text: str, **kw) -> list[DirectoryPlace]:
    raw = search(api_key, text, **kw)
    return [_to_place(item) for item in raw]
