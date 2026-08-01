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


# ---------------- identity dedup (Google returns the same biz N times) -------
@pytest.mark.parametrize("a,b", [
    ("JC's Landscaping LLC", "JC's Landscaping"),
    ("JC's Landscaping LLC", "Jc's landscaping, llc"),
    ("Ryno Lawn Care, LLC", "Ryno Lawn Care"),
    ("Green Co Inc", "Green"),
])
def test_normalize_name_folds_variants_together(a, b):
    from app.stages.discover import normalize_name
    assert normalize_name(a) == normalize_name(b)


def test_normalize_name_keeps_different_businesses_apart():
    from app.stages.discover import normalize_name
    assert normalize_name("JC's Landscaping") != normalize_name("JD's Landscaping")


def test_discover_dedups_the_same_business_under_different_place_ids(session):
    """The real defect: 'JC's Landscaping LLC' was discovered three times."""
    from app.adapters.places import BusinessCandidate, StubPlacesSource
    from app.stages.discover import discover

    addr = "1120 Parkwood Blvd, Frisco, TX 75034"
    source = StubPlacesSource([
        BusinessCandidate("p1", "JC's Landscaping LLC", "Frisco, TX", "lawn", address=addr),
        BusinessCandidate("p2", "JC's Landscaping", "Frisco, TX", "lawn", address=addr),
        BusinessCandidate("p3", "Jc's Landscaping, LLC", "Frisco, TX", "lawn", address=addr),
        BusinessCandidate("p4", "Ryno Lawn Care", "Frisco, TX", "lawn", address="9 Elm St"),
    ])
    created = discover(session, source, "Frisco, TX", None)
    assert [b.name for b in created] == ["JC's Landscaping LLC", "Ryno Lawn Care"]


def test_discover_does_not_re_add_on_a_second_run(session):
    """Re-running discovery must not duplicate rows already in the DB."""
    from app.adapters.places import BusinessCandidate, StubPlacesSource
    from app.stages.discover import discover

    addr = "1120 Parkwood Blvd, Frisco, TX"
    first = StubPlacesSource([
        BusinessCandidate("p1", "JC's Landscaping LLC", "Frisco, TX", "lawn", address=addr)])
    second = StubPlacesSource([  # same business, new place_id
        BusinessCandidate("p9", "JC's Landscaping", "Frisco, TX", "lawn", address=addr)])

    assert len(discover(session, first, "Frisco, TX", None)) == 1
    session.flush()
    assert discover(session, second, "Frisco, TX", None) == []
