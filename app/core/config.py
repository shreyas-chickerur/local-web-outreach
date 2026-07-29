"""Runtime configuration.

Phase 1 keeps this deliberately tiny (env-driven). Production target is
PostgreSQL; dev/test default to a local SQLite file so the suite runs with
zero external dependencies.
"""

from __future__ import annotations

import os

DEFAULT_SQLITE_URL = "sqlite+pysqlite:///./local_web_outreach.db"


def database_url() -> str:
    """Return the active database URL (``DATABASE_URL`` env var or SQLite default)."""
    return os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)
