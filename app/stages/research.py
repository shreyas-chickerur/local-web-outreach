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


def _norm_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


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
        for claim in group:
            by_value.setdefault(_norm_value(claim.value), []).append(claim)

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
