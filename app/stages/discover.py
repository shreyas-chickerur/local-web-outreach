"""Stage 1: DISCOVER.

Turn a location into persisted ``Business`` rows at status ``DISCOVERED``,
applying the geo-gate (US-only initially) and de-duplicating both within the
batch and against the existing DB. Every created row is audited.

Dedup uses ``place_id`` **and** a normalized name+address identity, because
Google returns the same business under several place_ids.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.places import BusinessCandidate, PlacesSource
from app.core.audit import record_event
from app.core.enums import Actor, BusinessStatus
from app.models.business import Business

_LEGAL_SUFFIXES = (" llc", " inc", " ltd", " co", " corp", " company", " lp", " plc")


def normalize_name(name: str) -> str:
    """Fold a business name to a comparable key.

    Google returned 'JC's Landscaping LLC' three times under different
    place_ids, so place_id alone under-dedups. Strips punctuation, casing, and
    legal suffixes: "JC's Landscaping LLC" -> "jcs landscaping".
    """
    folded = re.sub(r"[^a-z0-9\s]", "", (name or "").lower())
    folded = re.sub(r"\s+", " ", folded).strip()
    changed = True
    while changed:  # "Foo Co Inc" -> "foo"
        changed = False
        for suffix in _LEGAL_SUFFIXES:
            if folded.endswith(suffix):
                folded, changed = folded[: -len(suffix)].strip(), True
    return folded


def normalize_address(address: str | None) -> str:
    """Address key ignoring casing and punctuation."""
    folded = re.sub(r"[^a-z0-9\s]", "", (address or "").lower())
    return re.sub(r"\s+", " ", folded).strip()


def identity_key(name: str, address: str | None) -> str:
    """Two candidates sharing this key are treated as the same business."""
    return f"{normalize_name(name)}|{normalize_address(address)}"


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
    seen_identities: set[str] = set()

    # Existing identities, so a re-run doesn't re-add the same business under a
    # different place_id.
    known_identities = {
        identity_key(name, address)
        for name, address in session.execute(select(Business.name, Business.address)).all()
    }

    for candidate in source.search(location, category):
        if not is_us(candidate):
            continue
        if candidate.place_id in seen_in_batch:
            continue
        seen_in_batch.add(candidate.place_id)

        identity = identity_key(candidate.name, candidate.address)
        if identity in seen_identities or identity in known_identities:
            continue
        seen_identities.add(identity)

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
