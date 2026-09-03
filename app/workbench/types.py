"""The few shared types the workbench needs.

Small and self-contained on purpose: v1 kept these in a `core` package that also
owned a database session, an audit ledger, and a state machine, so importing an
enum pulled in SQLAlchemy. Nothing here touches storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SourceType(StrEnum):
    """Where a claim came from. Independence is what makes corroboration mean
    something, so the type is recorded per claim."""

    GBP = "google"           # Google Business Profile / Places
    YELP = "yelp"
    OSM = "openstreetmap"
    EXISTING_SITE = "their_site"
    OTHER = "other"


class Confidence(StrEnum):
    """How much weight a fact carries."""

    VERIFIED = "verified"        # >= 2 independent sources agree
    UNVERIFIED = "unverified"    # a single source says so
    CONFLICT = "conflict"        # sources disagree — never presented as fact
    # A named human checked it. Ships like VERIFIED, recorded separately so
    # machine corroboration and human judgement are never confused.
    OPERATOR_VERIFIED = "operator_verified"


@dataclass(frozen=True)
class RawClaim:
    """One source saying one thing about one field."""

    field: str
    value: str
    source_url: str
    source_type: SourceType
