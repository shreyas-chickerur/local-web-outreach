"""Stage 1: DISCOVER.

Turn a location into persisted ``Business`` rows at status ``DISCOVERED``,
applying the geo-gate (US-only initially) and de-duplicating by ``place_id``
both within the batch and against the existing DB. Every created row is audited.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.places import BusinessCandidate, PlacesSource
from app.core.audit import record_event
from app.core.enums import Actor, BusinessStatus
from app.models.business import Business


def is_us(candidate: BusinessCandidate) -> bool:
    """Geo-gate: only US businesses proceed (CAN-SPAM is permissive; CASL/GDPR
    require consent, so Canada/EU are excluded until an opt-in path exists)."""
    return (candidate.country or "US").upper() == "US"


def discover(
    session: Session,
    source: PlacesSource,
    location: str,
    category: str | None = None,
) -> list[Business]:
    """Fetch, geo-gate, dedup, and persist candidates as DISCOVERED businesses."""
    created: list[Business] = []
    seen_in_batch: set[str] = set()

    for candidate in source.search(location, category):
        if not is_us(candidate):
            continue
        if candidate.place_id in seen_in_batch:
            continue
        seen_in_batch.add(candidate.place_id)

        already = session.execute(
            select(Business).where(Business.place_id == candidate.place_id)
        ).scalar_one_or_none()
        if already is not None:
            continue

        biz = Business(
            name=candidate.name,
            location=candidate.location,
            category=candidate.category,
            place_id=candidate.place_id,
            address=candidate.address,
            phone=candidate.phone,
            existing_site_url=candidate.website,
            geo_country=(candidate.country or "US").upper(),
            status=BusinessStatus.DISCOVERED,
        )
        session.add(biz)
        session.flush()
        record_event(
            session,
            actor=Actor.SYSTEM.value,
            action="discover:created",
            subject_type="business",
            subject_id=biz.id,
            after={"name": biz.name, "place_id": biz.place_id, "location": biz.location},
        )
        created.append(biz)

    return created
