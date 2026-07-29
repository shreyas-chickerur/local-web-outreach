"""Stage 3 prerequisite: entity resolution.

The M0 demo showed aggregators conflate distinct local businesses ("Kane's
Landscaping" vs "Dan Kane Landscaping"; four "Amigos" across the metroplex). If
we research a wrongly-merged entity, every downstream claim is poisoned. So
before any claim extraction we canonicalize the target and keep only the sources
we can confidently tie to it — refusing to merge the rest.

Matching is intentionally conservative: a source is kept only if it corroborates
the target on a strong signal (phone or address) or on the name with no
conflicting phone. Anything ambiguous is rejected, not merged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.research_runner import SourceRecord


@dataclass(frozen=True)
class TargetEntity:
    name: str
    address: str | None = None
    phone: str | None = None


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _name_tokens(value: str | None) -> set[str]:
    # Drop generic suffixes so "Kane's Landscaping" vs "Kane's Landscaping LLC" match,
    # but "Kane's Landscaping" vs "Kane Lawn and Garden" do not.
    stop = {"llc", "inc", "co", "company", "the", "and", "&"}
    return {t for t in re.findall(r"[a-z0-9]+", _norm(value)) if t not in stop}


def _name_similarity(a: str, b: str) -> float:
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def matches(target: TargetEntity, source: SourceRecord, *, name_threshold: float = 0.6) -> bool:
    """True if ``source`` can be confidently tied to ``target``."""
    tphone, sphone = _digits(target.phone), _digits(source.entity_phone)
    # A phone that disagrees is a hard reject even if the name is similar.
    if tphone and sphone and tphone != sphone:
        return False
    if tphone and sphone and tphone == sphone:
        return True
    if target.address and source.entity_address and _norm(target.address) == _norm(
        source.entity_address
    ):
        return True
    return _name_similarity(target.name, source.entity_name) >= name_threshold


def resolve(
    target: TargetEntity, sources: list[SourceRecord]
) -> tuple[list[SourceRecord], list[SourceRecord]]:
    """Partition ``sources`` into (kept, rejected) for the canonical target."""
    kept: list[SourceRecord] = []
    rejected: list[SourceRecord] = []
    for source in sources:
        (kept if matches(target, source) else rejected).append(source)
    return kept, rejected
