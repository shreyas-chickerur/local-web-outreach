"""Runtime configuration.

Phase 1 keeps this deliberately tiny (env-driven). Production target is
PostgreSQL; dev/test default to a local SQLite file so the suite runs with
zero external dependencies.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load a local .env if present (never overrides already-set environment vars).
load_dotenv()

DEFAULT_SQLITE_URL = "sqlite+pysqlite:///./local_web_outreach.db"


def database_url() -> str:
    """Return the active database URL (``DATABASE_URL`` env var or SQLite default)."""
    return os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)


def places_provider() -> str:
    """Which places data source to use for live runs (default: google)."""
    return os.environ.get("PLACES_PROVIDER", "google").lower()


def google_places_api_key() -> str | None:
    """The Google Places API key, if configured (only needed for live discovery)."""
    return os.environ.get("GOOGLE_PLACES_API_KEY")


def yelp_api_key() -> str | None:
    """The Yelp Fusion API key, if configured.

    Lives here rather than in the adapter so it is read *after* the
    ``load_dotenv()`` above — an adapter reading ``os.environ`` directly only
    sees the key when this module happens to be imported first.
    """
    return os.environ.get("YELP_API_KEY", "").strip() or None


def preview_base_url() -> str:
    """Where generated site previews are served from.

    Locally this is the console itself; in production it becomes the public host
    that prospects can open. The token in the path is what keeps it private.
    """
    return os.environ.get("PREVIEW_BASE_URL", "http://127.0.0.1:8090").rstrip("/")


def sender_name() -> str:
    """Display name used in the CAN-SPAM email footer."""
    return os.environ.get("SENDER_NAME", "Local Web Outreach")


def sender_postal_address() -> str:
    """Physical postal address for the CAN-SPAM footer.

    A real mailing address is legally required for cold email — set
    SENDER_POSTAL_ADDRESS before sending. The default is an obvious placeholder.
    """
    return os.environ.get("SENDER_POSTAL_ADDRESS", "123 Example St, Frisco, TX 75034")
