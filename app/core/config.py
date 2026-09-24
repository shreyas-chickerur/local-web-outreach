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




def anthropic_api_key() -> str | None:
    """The language model's key: it reads an instruction and returns decisions, never copy.

    Optional. Without it the deterministic phrase parser handles instructions
    on its own, understanding less and saying so.
    """
    return os.environ.get("ANTHROPIC_API_KEY", "").strip() or None


def anthropic_model() -> str | None:
    """The model that reads instructions and photographs, named in `.env`.

    The code names no model: which one is used is a setting, changed without a
    commit. Unset with a key present, a call fails with a reason and the phrase
    parser takes over, exactly as it does when the key is missing.
    """
    return os.environ.get("ANTHROPIC_MODEL", "").strip() or None


def design_model() -> str | None:
    """The model a design run and a chat edit use, named in `.env`."""
    return os.environ.get("DESIGN_MODEL", "").strip() or None
