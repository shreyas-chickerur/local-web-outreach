"""Ten corroborated facts — eight of BRIEF §5's nine contractor facts, plus
the two credential facts `signature.py`'s `stamp` device needs to stop
asserting for free.

The generator used to carry none of service area, licensed and insured,
before-and-after, financing, emergency availability, warranty, manufacturer
badges, response time, or free estimate. Building all nine as page furniture
before any of them could be trusted was the wrong order — every one is a
claim about the business, and the content gate (`render.unsupported`)
rejects a build that asserts something the material does not back.

Eight of the nine ship as the `credentials` section: licensed and insured,
emergency availability, warranty, free estimate, service area, financing,
manufacturer badges (found as a named certification — "VELUX Certified
Installer" is exactly this claim, whether or not a badge image exists
anywhere in the material), and response time. Only **before-and-after**
remains unattempted: it needs a PAIRED photograph (a labelled "before" and
a labelled "after" of the same job), and nothing in the photo-labelling
pipeline captures that pairing today — `photo_notes`/`alt_for()` was
checked against the whole corpus and found exactly one incidental use of
the word "after" ("...a collision", not a job), which is evidence the
material does not carry this, not evidence to build around. Approximating
it without a real pair is the "invent a licence number" failure this
project explicitly refuses to do.

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
what it matched. The four newest patterns were checked against the whole
19-fixture corpus for false positives before landing — an earlier, looser
`service_area` pattern (any "serve"/"service" near a capitalised word)
matched "great service you deserve" and "we must preserve the family
dynamic" on businesses that never named a service area at all, and was
tightened to specific trigger phrases before being kept.
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
    ContractorFact(
        "service_area", "Service area",
        re.compile(r"\bservice area\b|\bareas we serve\b|\bproudly serving\b|"
                   r"what areas.{0,30}(?:do (?:you|we) )?serve",
                   re.IGNORECASE)),
    ContractorFact(
        "financing", "Financing available",
        re.compile(r"\bfinancing\b|\bpayment plans?\b|0%\s*apr|"
                   r"buy now,?\s*pay later", re.IGNORECASE)),
    ContractorFact(
        "manufacturer_badge", "Manufacturer certified",
        re.compile(r"authorized dealer|factory[\s-]certified|"
                   r"certified installer|master elite|comfort specialist|"
                   r"factory authorized", re.IGNORECASE)),
    ContractorFact(
        "response_time", "Fast response",
        re.compile(r"\bsame[\s-]day service\b|\bsame[\s-]day response\b|"
                   r"\d+[\s-]?(?:minute|hour|hr|min)s?\s*"
                   r"(?:response|callback|arrival)|respond within \d+",
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
