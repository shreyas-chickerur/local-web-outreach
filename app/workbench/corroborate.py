"""Turning what several sources said into facts with a confidence.

The rule: a value supported by **two independent sources** is VERIFIED, one
source is UNVERIFIED, and sources that disagree produce a CONFLICT that is never
presented as fact. Nothing is guessed and nothing is averaged away.

Most of the subtlety is in deciding whether two sources actually disagree.
They almost never write a fact identically — Google appends ", USA", Yelp writes
"Suite 100" where Google writes "#100", one omits the street type entirely.
Comparing raw strings turns agreement into conflict, which is worse than
useless: it buries a fact both sources confirmed. So comparison is field-aware,
while a genuine disagreement (a different street, a rating a full point apart)
still conflicts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field as dc_field

from app.workbench.types import Confidence, RawClaim

_COUNTRY_SUFFIXES = (", usa", ", united states", ", us")
_STREET_ABBREV = {
    "street": "st", "road": "rd", "avenue": "ave", "boulevard": "blvd",
    "drive": "dr", "lane": "ln", "parkway": "pkwy", "court": "ct",
    "highway": "hwy", "suite": "ste", "north": "n", "south": "s",
    "east": "e", "west": "w",
}
# Dropped before comparing: Google writes "Preston On The Lake Blvd", Yelp
# writes "Preston On The Lake". Number, street name, city and ZIP must still
# match, so this stays specific.
_STREET_TYPES = {"st", "rd", "ave", "blvd", "dr", "ln", "pkwy", "ct", "hwy",
                 "cir", "ter", "pl", "way", "trl"}
# "#100", "Suite 100", "Ste 100", "Unit 100" are the same door.
_UNIT_WORDS = {"ste", "suite", "apt", "unit", "no", "num", "bldg", "building", "fl"}
# OpenStreetMap spells the state out where Google and Yelp abbreviate it, which
# made three sources reporting one address look like a three-way disagreement.
_STATES = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
    "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de",
    "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id",
    "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks",
    "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
    "massachusetts": "ma", "michigan": "mi", "minnesota": "mn",
    "mississippi": "ms", "missouri": "mo", "montana": "mt", "nebraska": "ne",
    "nevada": "nv", "ohio": "oh", "oklahoma": "ok", "oregon": "or",
    "pennsylvania": "pa", "tennessee": "tn", "texas": "tx", "utah": "ut",
    "vermont": "vt", "virginia": "va", "washington": "wa", "wisconsin": "wi",
    "wyoming": "wy",
}

# Numeric fields agree within a tolerance rather than exactly. A star rating
# summarises a different crowd on each platform; half a star apart is the same
# verdict. A tolerance avoids the arbitrary split a bucket boundary creates.
_TOLERANT_FIELDS = {"rating": 0.5}


@dataclass(frozen=True)
class Fact:
    field: str
    value: str | None
    confidence: Confidence
    score: float
    corroborations: int
    sources: list[dict]
    # For a CONFLICT, who said what. Two values joined by a pipe are unreadable —
    # the question is always which source to believe.
    candidates: list[dict] = dc_field(default_factory=list)

    @property
    def is_fact(self) -> bool:
        return self.confidence in (Confidence.VERIFIED, Confidence.OPERATOR_VERIFIED)


def _norm_generic(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _norm_phone(value: str) -> str:
    """Digits only, last 10, so a +1 prefix and punctuation don't matter."""
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 10 else digits


def _norm_address(value: str) -> str:
    text = _norm_generic(value)
    for suffix in _COUNTRY_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    text = re.sub(r"[.,#]", " ", text)
    words = [_STATES.get(w, _STREET_ABBREV.get(w, w)) for w in text.split()]
    return " ".join(
        w for w in words if w not in _STREET_TYPES and w not in _UNIT_WORDS
    ).strip()


def normalize(value: str, field_name: str = "") -> str:
    if field_name == "phone":
        return _norm_phone(value)
    if field_name == "address":
        return _norm_address(value)
    return _norm_generic(value)


def _within_tolerance(claims: list[RawClaim], field_name: str) -> bool:
    try:
        values = [float(c.value) for c in claims]
    except (TypeError, ValueError):
        return False
    return bool(values) and (max(values) - min(values)) <= _TOLERANT_FIELDS[field_name]


def corroborate(claims: list[RawClaim]) -> list[Fact]:
    """Group claims by field and score each by how many sources back it."""
    by_field: dict[str, list[RawClaim]] = {}
    for claim in claims:
        by_field.setdefault(claim.field, []).append(claim)

    facts: list[Fact] = []
    for field_name, group in by_field.items():
        by_value: dict[str, list[RawClaim]] = {}
        if field_name in _TOLERANT_FIELDS and _within_tolerance(group, field_name):
            by_value[normalize(group[0].value, field_name)] = list(group)
        else:
            for claim in group:
                by_value.setdefault(normalize(claim.value, field_name), []).append(claim)

        all_sources = [{"source_type": c.source_type.value, "source_url": c.source_url}
                       for c in group]

        if len(by_value) > 1:
            facts.append(Fact(
                field=field_name,
                value=" | ".join(sorted({c.value for c in group})),
                confidence=Confidence.CONFLICT,
                score=0.3,
                corroborations=len(all_sources),
                sources=all_sources,
                candidates=[{"value": c.value, "source_type": c.source_type.value,
                             "source_url": c.source_url} for c in group],
            ))
            continue

        winning = next(iter(by_value.values()))
        distinct = len({c.source_url for c in winning})
        facts.append(Fact(
            field=field_name,
            value=winning[0].value,
            confidence=Confidence.VERIFIED if distinct >= 2 else Confidence.UNVERIFIED,
            score=min(0.6 + 0.15 * distinct, 0.98) if distinct >= 2 else 0.5,
            corroborations=distinct,
            sources=[{"source_type": c.source_type.value, "source_url": c.source_url}
                     for c in winning],
        ))
    return facts
