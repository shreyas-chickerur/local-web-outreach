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


# One place, because two drifted. The default said 8090 while the server has
# always served 8099, so every absolute URL built from it — the og:image in a
# link preview, most visibly — pointed at a dead port.
DEFAULT_PORT = 8099


def preview_base_url() -> str:
    """Where generated site previews are served from.

    Used for anything that must be fetchable from somewhere other than this
    process: a phone rendering the link preview when the operator texts it.
    """
    return os.environ.get(
        "PREVIEW_BASE_URL", f"http://127.0.0.1:{DEFAULT_PORT}").rstrip("/")


def anthropic_api_key() -> str | None:
    """Claude — reads an instruction and returns decisions, never copy.

    Optional. Without it the deterministic phrase parser handles instructions
    on its own, understanding less and saying so.
    """
    return os.environ.get("ANTHROPIC_API_KEY", "").strip() or None


def anthropic_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5").strip()
