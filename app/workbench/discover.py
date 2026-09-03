"""Find prospects near a point, by category.

One paid request per category returns the businesses; their own websites are
then read for the two signals Google cannot give us — whether the site is built
for phones, and whether it loads at all. Those reads are the slow part, so they
run in a small thread pool and the whole group is cached.
"""

from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from app.adapters.gplaces import PlacesError, places
from app.adapters.site_fetch import HttpSiteFetcher, SiteFetcher
from app.workbench.brief import alternate_urls, site_state
from app.workbench.categories import CATEGORIES, Category
from app.workbench.extract import extract_from_html
from app.workbench.prospect import Prospect, rank

CACHE_HOURS = 24
CHAIN_AT = 3          # locations under one name before we call it a chain
THIN_WORDS = 220      # fewer visible words than this and there is no site here


def _cached(conn: sqlite3.Connection, key: str) -> list[dict] | None:
    row = conn.execute("SELECT payload, fetched_at FROM discovery_cache WHERE key = ?",
                       (key,)).fetchone()
    if row is None:
        return None
    age = datetime.now(UTC) - datetime.fromisoformat(row["fetched_at"])
    if age > timedelta(hours=CACHE_HOURS):
        return None
    return list(json.loads(row["payload"]))


def _store(conn: sqlite3.Connection, key: str, payload: list[dict]) -> None:
    conn.execute(
        "INSERT INTO discovery_cache (key, payload, fetched_at) VALUES (?,?,?)"
        " ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,"
        " fetched_at=excluded.fetched_at",
        (key, json.dumps(payload), datetime.now(UTC).isoformat(timespec="seconds")))


def _inspect(prospect: Prospect, fetcher: SiteFetcher) -> Prospect:
    """Read their site for what Google cannot tell us. Never raises."""
    if not prospect.website:
        return prospect
    try:
        result = fetcher.fetch(prospect.website)
    except Exception:                       # a bad site must not sink the page
        return prospect
    if getattr(result, "tls_error", False):
        # The published address throws a security warning. That is a finding
        # about them, not a reason for us to give up reading the site.
        prospect.cert_error = True
        for candidate in alternate_urls(prospect.website):
            try:
                retry = fetcher.fetch(candidate)
            except Exception:
                continue
            if retry.ok and retry.html:
                result = retry
                break
    state = site_state(result.status, bool(result.ok and result.html))
    # Being refused is not being broken, and it says nothing about the business.
    prospect.site_reachable = None if state == "blocked" else (state == "ok")
    if not result.html:
        return prospect
    site = extract_from_html(result.html, result.final_url or prospect.website)
    prospect.mobile_ready = site.mobile_ready
    prospect.https = str(result.final_url or "").lower().startswith("https")
    prospect.js_rendered = site.js_rendered
    # Measured on the page, not on what our parser managed to pull out of it.
    prospect.thin_site = site.text_words < THIN_WORDS
    return prospect


def find(conn: sqlite3.Connection, api_key: str, latitude: float, longitude: float,
         category: Category, *, limit: int = 12, radius_m: float = 15000.0,
         fetcher: SiteFetcher | None = None, refresh: bool = False) -> list[dict]:
    key = f"{category.key}|{latitude:.3f},{longitude:.3f}|{int(radius_m)}"
    if not refresh:
        hit = _cached(conn, key)
        if hit is not None:
            return hit

    found = places(api_key, category.query, latitude=latitude, longitude=longitude,
                   radius_m=radius_m, limit=limit)
    # A brand appearing several times in one search is a chain, whoever it is.
    counts: dict[str, int] = {}
    for place in found:
        counts[place.name.lower()] = counts.get(place.name.lower(), 0) + 1

    candidates = [
        Prospect(name=p.name, address=p.address, website=p.website, phone=p.phone,
                 rating=p.rating, reviews=p.review_count, category=category.key,
                 summary=p.summary, source_url=p.source_url,
                 business_status=p.business_status,
                 is_chain=counts.get(p.name.lower(), 1) >= CHAIN_AT)
        for p in found]

    reader = fetcher or HttpSiteFetcher(timeout=8.0)
    with ThreadPoolExecutor(max_workers=8) as pool:
        candidates = list(pool.map(lambda c: _inspect(c, reader), candidates))

    payload = [vars(p) for p in rank(candidates)]
    _store(conn, key, payload)
    return payload


def find_all(conn: sqlite3.Connection, api_key: str, latitude: float,
             longitude: float, *, categories=CATEGORIES, **kw) -> list[dict]:
    """Every category as its own group, best prospects first inside each."""
    groups: list[dict] = []
    for category in categories:
        try:
            prospects = find(conn, api_key, latitude, longitude, category, **kw)
            error = None
        except PlacesError as exc:
            prospects, error = [], str(exc)
        groups.append({"key": category.key, "label": category.label,
                       "blurb": category.blurb, "prospects": prospects,
                       "error": error})
    return groups
