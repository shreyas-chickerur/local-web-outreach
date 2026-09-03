"""Runtime configuration — environment only, no storage.

v2 needs three things: which lookup sources are available, and where previews
will eventually be served. Anything that existed to make sending email safe is
gone with the sending.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load a local .env if present (never overrides already-set environment vars).
load_dotenv()


def google_places_api_key() -> str | None:
    """Google Places — the only source that reliably returns a business's own
    website, which is what answers 'do they even have one?'."""
    return os.environ.get("GOOGLE_PLACES_API_KEY", "").strip() or None


def yelp_api_key() -> str | None:
    """Yelp Fusion — covers the local service businesses OpenStreetMap misses."""
    return os.environ.get("YELP_API_KEY", "").strip() or None


def preview_base_url() -> str:
    """Where generated site previews will be served from (slice 3)."""
    return os.environ.get("PREVIEW_BASE_URL", "http://127.0.0.1:8090").rstrip("/")
