"""Single source of the current UTC time.

Centralized so models and services share one timezone-aware ``now`` (and tests
have one seam to patch), instead of each module defining its own ``_utcnow``.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Timezone-aware current time in UTC."""
    return datetime.now(UTC)


def as_aware(value: datetime | None) -> datetime | None:
    """Force a datetime to be timezone-aware (UTC).

    SQLite does not store timezones, so a datetime written as aware reads back
    naive. Comparing that against ``utcnow()`` raises. Every read of a stored
    timestamp that will be compared must pass through here.
    """
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
