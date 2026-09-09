"""Six corroborated facts — four of BRIEF §5's nine contractor facts, plus
the two credential facts `signature.py`'s `stamp` device needs to stop
asserting for free.

The generator has never carried service area, licensed and insured,
before-and-after, financing, emergency availability, warranty, manufacturer
badges, response time, or free estimate. Building all nine as page furniture
before any of them could be trusted was the wrong order — every one is a
claim about the business, and the content gate (`render.unsupported`)
rejects a build that asserts something the material does not back.

Four of the nine ship as the `credentials` section: licensed and insured,
emergency availability, warranty, and free estimate. The other five (service
area, before-and-after, financing, manufacturer badges, response time) need
a different kind of evidence this material does not carry yet — a
service-area radius, a paired before/after photo, a named lender, a
recognisable badge image, a stated callback window — and are not attempted
here rather than faked. See `.reviews/slice-b-phase-2.md`.

TWO MORE — `admitted_to_bar`, `registered_practice` — exist only so
`stamp` has something to check. That device shipped "Licensed & insured" /
"Registered practice" / "Admitted to the bar" unconditionally on
`trade_kind` alone, on six fixtures whose own material corroborated none of
it (`hvac-rich`, `hvac-second`, `law-rich`, `law`, `roofer-rich`,
`threadbare` — the worst being `threadbare`, which has no about text, no
content blocks and one photograph, asserting a licence four times anyway).
See `.reviews/slice-c-credential-claims.md`.

Every fact here is found by matching a fixed phrase against the business's
OWN published text — `Material.about` and the raw `blocks` a scrape kept,
never generated and never inferred from the trade. A phrase that is not
actually there is a fact that is not there either; `found()` returns only
what it matched.
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
# might print. Every one of these six is never emitted unless the pattern
# actually matched.
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
    # `stamp`'s `desk` mark. "State bar" alone (without "admitted") is
    # included because a firm bio just as often reads "member of the Texas
    # State Bar" as "admitted to the bar" — both are the same claim.
    ContractorFact(
        "admitted_to_bar", "Admitted to the bar",
        re.compile(r"admitted to the (?:state )?bar|\bstate bar\b",
                   re.IGNORECASE)),
    # `stamp`'s `care` mark. "Registered" alone is too broad — "registered
    # trademark" and "register for an appointment" are not this claim — so
    # this requires the credential word next to a practice/accreditation
    # word rather than "registered" on its own.
    ContractorFact(
        "registered_practice", "Registered practice",
        re.compile(r"registered (?:practice|dental practice|clinic)|"
                   r"board[- ]certified|accredited practice",
                   re.IGNORECASE)),
)

_BY_KEY = {fact.key: fact for fact in FACTS}

# Which fact corroborates `signature.py`'s `stamp` device, per `trade_kind`.
# `stamp`'s own MARK text lives in signature.py (it is a §2.3 device
# concern); this is only the evidence a mark needs before it can render.
STAMP_FACT: dict[str, str] = {
    "trade": "licensed_insured",
    "care": "registered_practice",
    "desk": "admitted_to_bar",
}


def found(text: str) -> tuple[str, ...]:
    """Which fact keys this exact text corroborates, in `FACTS` order.

    Order matters downstream: the fingerprint and the section builder both
    read this list positionally, so a stable order is part of the contract,
    not an implementation detail.
    """
    return tuple(fact.key for fact in FACTS if fact.pattern.search(text or ""))


def label_for(key: str) -> str:
    return _BY_KEY[key].label
