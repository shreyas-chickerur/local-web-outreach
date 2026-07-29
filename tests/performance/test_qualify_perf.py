"""Performance guardrail for qualification throughput (probe injected, so this
measures the stage logic + spine writes, not the network)."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from app.adapters.site_fetch import FetchResult
from app.core.enums import BusinessStatus as S
from app.models.business import Business
from app.stages.qualify import SiteProber, qualify

pytestmark = pytest.mark.performance

N = 500
NOW = datetime(2026, 7, 29, tzinfo=UTC)


class NoSiteFetcher:
    def fetch(self, url: str) -> FetchResult:  # never called for no-site path
        return FetchResult(ok=False, status=404, final_url=url, html="", elapsed_ms=0)


def test_qualify_throughput(session, capsys):
    businesses = []
    for i in range(N):
        biz = Business(name=f"Biz {i}", location="Frisco, TX", place_id=f"p{i}",
                       existing_site_url=None, status=S.DISCOVERED)
        session.add(biz)
        businesses.append(biz)
    session.flush()

    prober = SiteProber(NoSiteFetcher(), now=NOW)
    start = time.perf_counter()
    for biz in businesses:
        qualify(session, biz, prober)
    session.commit()
    elapsed = time.perf_counter() - start
    rate = N / elapsed

    with capsys.disabled():
        print(f"\n[perf] qualify: {N} businesses in {elapsed:.3f}s -> {rate:,.0f}/s")

    assert all(b.status is S.QUALIFIED for b in businesses)
    assert rate > 40, f"qualify throughput too low: {rate:.0f}/s"
