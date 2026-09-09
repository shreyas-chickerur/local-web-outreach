"""Four of BRIEF §5's nine contractor facts, each corroborated or absent.

The generator has never carried service area, licensed and insured,
before-and-after, financing, emergency availability, warranty, manufacturer
badges, response time, or free estimate. Building all nine as page furniture
before any of them could be trusted was the wrong order — every one is a
claim about the business, and the existing content gate
(`render.unsupported`) rejects a build that asserts something the material
does not back.

This module ships four: licensed and insured, emergency availability,
warranty, and free estimate. Each is found by matching a fixed phrase against
the business's OWN published text — `Material.about` and the raw `blocks` a
scrape kept, never generated and never inferred from the trade. A phrase that
is not actually there is a fact that is not there either; `found()` returns
only what it matched, and a business with none of the four gets no section at
all rather than four empty ones.

The other five (service area, before-and-after, financing, manufacturer
badges, response time) need a different kind of evidence this material does
not carry yet — a service-area radius, a paired before/after photo, a named
lender, a recognisable badge image, a stated callback window — and are not
attempted here rather than faked. See `.reviews/slice-b-phase-2.md`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractorFact:
    key: str
    label: str
    pattern: re.Pattern[str]


# Patterns match the business's OWN phrasing, not a generic label the page
# might print — "licensed & insured" is what `signature.py`'s `stamp` device
# already prints unconditionally for every `trade`-kind business, whether or
# not it is true of THIS one. This does not fix that (a signature device is a
# `§2.3` concern, not a Slice C one), but its own corroborated version does
# not repeat the mistake: this module never emits its label unless the
# pattern matched.
FACTS: tuple[ContractorFact, ...] = (
    ContractorFact(
        "licensed_insured", "Licensed & insured",
        re.compile(r"licen[sc]ed\s*(?:(?:and|&|,)\s*)?insured", re.IGNORECASE)),
    ContractorFact(
        "emergency", "24/7 emergency service",
        re.compile(r"24\s*/\s*7\b|around[\s-]the[\s-]clock|"
                   r"emergency\s+(?:service|repair|plumb|hvac|response)",
                   re.IGNORECASE)),
    ContractorFact(
        "warranty", "Workmanship warranty",
        re.compile(r"\bwarrant(?:y|ies|ed)\b|\bworkmanship\s+guarantee\b",
                   re.IGNORECASE)),
    ContractorFact(
        "free_estimate", "Free estimate",
        re.compile(r"free\s+estimate|free\s+quote|no[\s-]obligation\s+quote",
                   re.IGNORECASE)),
)

_BY_KEY = {fact.key: fact for fact in FACTS}


def found(text: str) -> tuple[str, ...]:
    """Which fact keys this exact text corroborates, in `FACTS` order.

    Order matters downstream: the fingerprint and the section builder both
    read this list positionally, so a stable order is part of the contract,
    not an implementation detail.
    """
    return tuple(fact.key for fact in FACTS if fact.pattern.search(text or ""))


def label_for(key: str) -> str:
    return _BY_KEY[key].label
