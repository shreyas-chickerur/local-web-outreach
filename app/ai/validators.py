"""Output validators — the hard guards on extracted claims (invariant #1)."""

from __future__ import annotations

from collections.abc import Iterable

from app.ai.research_runner import RawClaim
from app.core.errors import ResearchIntegrityError


def validate_raw_claims(claims: Iterable[RawClaim]) -> list[RawClaim]:
    """Reject any claim lacking a source_url. No fact ships without provenance."""
    validated: list[RawClaim] = []
    for claim in claims:
        if not claim.source_url or not claim.source_url.strip():
            raise ResearchIntegrityError(
                f"claim {claim.field}={claim.value!r} has no source_url"
            )
        if not claim.value or not str(claim.value).strip():
            raise ResearchIntegrityError(f"claim {claim.field} has an empty value")
        validated.append(claim)
    return validated
