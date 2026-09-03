"""Stage 3: RESEARCH.

Given a business and a set of collected sources, produce a dossier of atomic,
sourced, confidence-scored claims:

  entity resolution -> extract -> validate -> corroborate -> persist + audit.

Confidence comes from corroboration: a field value supported by >= 2 independent
sources is VERIFIED; a single source is UNVERIFIED; disagreeing sources are a
CONFLICT (never shipped as fact). Required fields with no VERIFIED claim become
questions for the owner — gaps are surfaced, never fabricated.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from dataclasses import field as dc_field

from sqlalchemy.orm import Session

from app.ai.research_runner import ClaimExtractor, RawClaim, SourceRecord
from app.ai.validators import validate_raw_claims
from app.core.audit import record_event
from app.core.enums import Actor, ClaimStatus
from app.models.research_claim import ResearchClaim
from app.stages.entity_resolution import TargetEntity, resolve

# Fields a complete dossier should have a VERIFIED claim for; the rest become
# owner questions.
REQUIRED_FIELDS = ("address", "phone", "hours", "services", "owner_name")


@dataclass(frozen=True)
class ResolvedClaim:
    field: str
    value: str | None
    status: ClaimStatus
    confidence: float
    corroborations: int
    sources: list[dict]


@dataclass
class Dossier:
    business_id: uuid.UUID
    claims: list[ResolvedClaim] = dc_field(default_factory=list)
    questions: list[str] = dc_field(default_factory=list)
    rejected_sources: list[SourceRecord] = dc_field(default_factory=list)

    def verified(self) -> list[ResolvedClaim]:
        return [c for c in self.claims if c.status is ClaimStatus.VERIFIED]


# Two sources describing the SAME fact rarely format it identically. Google says
# "9500 Frisco St, Frisco, TX 75033"; Yelp says the same with ", USA" appended.
# Comparing raw strings turns that into a CONFLICT, which is worse than useless:
# it buries a fact both sources actually agree on. Normalization is field-aware,
# so a genuine disagreement (a different street) still conflicts.
_STREET_ABBREV = {
    "street": "st", "road": "rd", "avenue": "ave", "boulevard": "blvd",
    "drive": "dr", "lane": "ln", "parkway": "pkwy", "court": "ct",
    "highway": "hwy", "suite": "ste", "north": "n", "south": "s",
    "east": "e", "west": "w",
}
_COUNTRY_SUFFIXES = (", usa", ", united states", ", us")


def _norm_generic(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _norm_phone(value: str) -> str:
    """Compare phones by digits only; keep the last 10 so a +1 prefix matches."""
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 10 else digits


# Street-type words are dropped for comparison: Google writes "1800 Preston On
# The Lake Blvd", Yelp writes "1800 Preston On The Lake". The house number,
# street name, city and ZIP still have to match, so this stays specific.
_STREET_TYPES = {"st", "rd", "ave", "blvd", "dr", "ln", "pkwy", "ct", "hwy",
                 "cir", "ter", "pl", "way", "trl"}
# Unit designators are written every possible way for the same door:
# "#100", "Suite 100", "Ste 100", "Unit 100". Drop the word, keep the number.
_UNIT_WORDS = {"ste", "suite", "apt", "unit", "no", "num", "bldg", "building", "fl"}


def _norm_address(value: str) -> str:
    """Fold country suffix, punctuation, abbreviations, and street-type words."""
    text = _norm_generic(value)
    for suffix in _COUNTRY_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    text = re.sub(r"[.,#]", " ", text)
    words = [_STREET_ABBREV.get(w, w) for w in text.split()]
    return " ".join(
        w for w in words if w not in _STREET_TYPES and w not in _UNIT_WORDS
    ).strip()


# Fields compared numerically, with how far apart two sources may be and still
# be saying the same thing. A star rating is a summary of a different crowd on
# each platform; half a star apart is agreement, a point apart is not.
_TOLERANT_FIELDS = {"rating": 0.5}


def _within_tolerance(claims: list[RawClaim], field: str) -> bool:
    """True if every source's numeric value sits inside the field's tolerance."""
    try:
        values = [float(c.value) for c in claims]
    except (TypeError, ValueError):
        return False
    return bool(values) and (max(values) - min(values)) <= _TOLERANT_FIELDS[field]


def _norm_value(value: str, field: str = "") -> str:
    """Normalize a claim value for equality comparison, by field type."""
    if field == "phone":
        return _norm_phone(value)
    if field == "address":
        return _norm_address(value)
    return _norm_generic(value)


def corroborate(claims: list[RawClaim]) -> list[ResolvedClaim]:
    """Group claims by field, score confidence by independent-source count, and
    flag disagreements as conflicts."""
    by_field: dict[str, list[RawClaim]] = {}
    for claim in claims:
        by_field.setdefault(claim.field, []).append(claim)

    resolved: list[ResolvedClaim] = []
    for field_name, group in by_field.items():
        # Group by normalized value; count distinct source_urls per value.
        by_value: dict[str, list[RawClaim]] = {}
        if field_name in _TOLERANT_FIELDS and _within_tolerance(group, field_name):
            # Numeric fields agree within a tolerance rather than exactly: Google
            # and Yelp poll different crowds, so 4.7 and 5.0 are the same verdict.
            # Bucketing would split them at an arbitrary boundary; a tolerance
            # doesn't.
            by_value[_norm_value(group[0].value, field_name)] = list(group)
        else:
            for claim in group:
                by_value.setdefault(_norm_value(claim.value, field_name), []).append(claim)

        all_sources = [
            {"source_type": c.source_type.value, "source_url": c.source_url} for c in group
        ]

        if len(by_value) > 1:
            # Sources disagree on this field.
            candidates = " | ".join(sorted({c.value for c in group}))
            resolved.append(
                ResolvedClaim(
                    field=field_name,
                    value=candidates,
                    status=ClaimStatus.CONFLICT,
                    confidence=0.3,
                    corroborations=len(all_sources),
                    sources=all_sources,
                )
            )
            continue

        winning = next(iter(by_value.values()))
        distinct_sources = len({c.source_url for c in winning})
        if distinct_sources >= 2:
            status = ClaimStatus.VERIFIED
            confidence = min(0.6 + 0.15 * distinct_sources, 0.98)
        else:
            status = ClaimStatus.UNVERIFIED
            confidence = 0.5
        resolved.append(
            ResolvedClaim(
                field=field_name,
                value=winning[0].value,
                status=status,
                confidence=confidence,
                corroborations=distinct_sources,
                sources=[
                    {"source_type": c.source_type.value, "source_url": c.source_url}
                    for c in winning
                ],
            )
        )
    return resolved


def build_dossier(
    session: Session,
    business,  # noqa: ANN001 - app.models.business.Business
    sources: list[SourceRecord],
    extractor: ClaimExtractor,
    *,
    model_version: str | None = None,
) -> Dossier:
    """Full research pipeline for one business; persists claims + audits."""
    target = TargetEntity(
        name=business.name, address=business.address, phone=business.phone
    )
    kept, rejected = resolve(target, sources)

    raw_claims = validate_raw_claims(extractor.extract(kept))
    resolved = corroborate(raw_claims)

    for rc in resolved:
        session.add(
            ResearchClaim(
                business_id=business.id,
                field=rc.field,
                value=rc.value,
                status=rc.status,
                confidence=rc.confidence,
                corroborations=rc.corroborations,
                sources=rc.sources,
                model_version=model_version,
            )
        )
    session.flush()

    verified_fields = {c.field for c in resolved if c.status is ClaimStatus.VERIFIED}
    questions = [
        f"Can you confirm your {f.replace('_', ' ')}?"
        for f in REQUIRED_FIELDS
        if f not in verified_fields
    ]

    record_event(
        session,
        actor=Actor.SYSTEM.value,
        action="research:dossier_built",
        subject_type="business",
        subject_id=business.id,
        after={
            "claims": len(resolved),
            "verified": len(verified_fields),
            "conflicts": sum(1 for c in resolved if c.status is ClaimStatus.CONFLICT),
            "rejected_sources": len(rejected),
            "open_questions": len(questions),
        },
    )
    session.flush()

    return Dossier(
        business_id=business.id, claims=resolved, questions=questions, rejected_sources=rejected
    )
