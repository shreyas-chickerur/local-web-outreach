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
    """One source saying one thing about one field, and how it said it.

    A confidence score tells you how much to trust a fact. It does not let you
    check one. For that you need the source's own words and where in the source
    they were: "schema.org Restaurant \u00b7 telephone" and the string that sat
    there, or the sentence on the page a number was read out of.

    Both default to empty, and stay empty when a source has nothing to quote —
    a directory that answers with a bare field has no sentence, and inventing
    one to fill the column would be worse than leaving it blank.
    """

    field: str
    value: str
    source_url: str
    source_type: SourceType
    quote: str = ""       # what the source said, verbatim
    found_in: str = ""    # where in the source it was found
