"""Single source of the current UTC time.

Centralized so models and services share one timezone-aware ``now`` (and tests
have one seam to patch), instead of each module defining its own ``_utcnow``.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Timezone-aware current time in UTC."""
    return datetime.now(UTC)
