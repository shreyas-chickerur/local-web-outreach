"""End-to-end Stage 1+2: a realistic Frisco batch flows through discover +
qualify, producing the right statuses, weaknesses, and an intact audit chain."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.adapters.places import BusinessCandidate, StubPlacesSource
from app.adapters.site_fetch import FetchResult
from app.core.audit import verify_chain
from app.core.enums import BusinessStatus as S
from app.models.business import Business
from app.models.site_weakness import SiteWeakness
from app.stages.discover import discover
from app.stages.qualify import SiteProber, qualify

NOW = datetime(2026, 7, 29, tzinfo=UTC)

# A modern, healthy site (https, viewport, current copyright, fast).
HEALTHY = FetchResult(
    ok=True, status=200, final_url="https://depotcafefrisco.com",
    html='<html><head><meta name="viewport"></head><body>© 2026 Depot</body></html>',
    elapsed_ms=250,
)
# A dated site: http (no https) + stale copyright + no viewport.
DATED = FetchResult(
    ok=True, status=200, final_url="http://olddiner.example",
    html="<html><head></head><body>© 2017 Old Diner</body></html>", elapsed_ms=800,
)

FETCHER_MAP = {
    "https://depotcafefrisco.com": HEALTHY,
    "http://olddiner.example": DATED,
}


class FakeFetcher:
    def fetch(self, url: str) -> FetchResult:
        return FETCHER_MAP.get(
            url, FetchResult(ok=False, status=404, final_url=url, html="", elapsed_ms=0,
                             error="not found")
        )


def _frisco_batch() -> list[BusinessCandidate]:
    return [
        BusinessCandidate("depot", "The Depot Cafe", "Frisco, TX", "restaurant",
                          website="https://depotcafefrisco.com"),
        BusinessCandidate("jslawn", "JS Lawn Care Service", "Frisco, TX", "lawn",
                          website=None),
        BusinessCandidate("olddiner", "Old Diner", "Frisco, TX", "restaurant",
                          website="http://olddiner.example"),
        BusinessCandidate("mcd", "McDonald's Frisco", "Frisco, TX", "restaurant",
                          website="https://mcdonalds.com"),
        BusinessCandidate("poutine", "Poutine Palace", "Frisco, TX", "restaurant",
                          country="CA"),  # non-US -> excluded
        BusinessCandidate("jslawn", "JS Lawn (dup)", "Frisco, TX", "lawn"),  # dup place_id
    ]


def _run(session) -> dict[str, Business]:
    source = StubPlacesSource(_frisco_batch())
    created = discover(session, source, "Frisco, TX")
    prober = SiteProber(FakeFetcher(), now=NOW)
    for biz in created:
        qualify(session, biz, prober)
    session.commit()
    return {b.place_id: b for b in session.execute(select(Business)).scalars().all()}


@pytest.mark.functional
def test_frisco_flow_sqlite(session):
    by_id = _run(session)

    # non-US excluded, duplicate deduped -> 4 businesses persisted
    assert set(by_id) == {"depot", "jslawn", "olddiner", "mcd"}

    assert by_id["depot"].status is S.DISQUALIFIED   # healthy site, already covered
    assert by_id["depot"].has_site is True
    assert by_id["jslawn"].status is S.QUALIFIED      # no site -> lead
    assert by_id["jslawn"].has_site is False
    assert by_id["olddiner"].status is S.QUALIFIED    # dated site -> lead
    assert by_id["mcd"].status is S.DISQUALIFIED      # franchise

    # Old Diner should carry the http + stale + viewport weaknesses.
    issues = {
        w.issue
        for w in session.execute(
            select(SiteWeakness).where(SiteWeakness.business_id == by_id["olddiner"].id)
        ).scalars()
    }
    assert {"no_https", "stale_content", "not_mobile_responsive"} <= issues
    assert by_id["olddiner"].opportunity_score >= 5

    ok, bad = verify_chain(session)
    assert ok is True, f"audit chain broke at {bad}"


@pytest.mark.functional
@pytest.mark.postgres
def test_frisco_flow_postgres(pg_session):
    by_id = _run(pg_session)
    assert by_id["jslawn"].status is S.QUALIFIED
    assert by_id["depot"].status is S.DISQUALIFIED
    ok, bad = verify_chain(pg_session)
    assert ok is True and bad is None
