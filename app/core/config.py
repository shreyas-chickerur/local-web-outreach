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
