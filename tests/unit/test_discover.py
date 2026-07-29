"""Unit tests for Stage 1 discovery: geo-gate, de-duplication, persistence."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.adapters.places import BusinessCandidate, StubPlacesSource
from app.core.audit import verify_chain
from app.core.enums import BusinessStatus as S
from app.models.audit import AuditEvent
from app.models.business import Business
from app.stages.discover import discover

pytestmark = pytest.mark.unit


def cand(pid, name, country="US", website=None):
    return BusinessCandidate(
        place_id=pid, name=name, location="Frisco, TX", country=country, website=website
    )


def test_discover_persists_us_candidates_as_discovered(session):
    source = StubPlacesSource([cand("p1", "Acme"), cand("p2", "Beta")])
    created = discover(session, source, "Frisco, TX")
    assert len(created) == 2
    assert all(b.status is S.DISCOVERED for b in created)
    assert session.execute(select(func.count()).select_from(Business)).scalar_one() == 2


def test_guard_geo_gate_excludes_non_us(session):
    source = StubPlacesSource([cand("p1", "US Co", "US"), cand("p2", "CA Co", "CA")])
    created = discover(session, source, "Frisco, TX")
    names = {b.name for b in created}
    assert names == {"US Co"}  # Canadian business excluded, never persisted


def test_dedup_within_batch(session):
    source = StubPlacesSource([cand("dup", "First"), cand("dup", "Second")])
    created = discover(session, source, "Frisco, TX")
    assert len(created) == 1


def test_dedup_against_existing_db(session):
    source = StubPlacesSource([cand("p1", "Acme")])
    discover(session, source, "Frisco, TX")
    # second run with the same place_id must not create a duplicate row
    again = discover(session, source, "Frisco, TX")
    assert again == []
    assert session.execute(select(func.count()).select_from(Business)).scalar_one() == 1


def test_discover_audits_each_creation(session):
    source = StubPlacesSource([cand("p1", "Acme"), cand("p2", "Beta")])
    discover(session, source, "Frisco, TX")
    events = session.execute(
        select(AuditEvent).where(AuditEvent.action == "discover:created")
    ).scalars().all()
    assert len(events) == 2
    ok, bad = verify_chain(session)
    assert ok is True and bad is None
