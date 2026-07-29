"""Unit tests for Stage 2 qualification: site probing, weakness detection,
scoring, franchise exclusion, and spine integration."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.adapters.site_fetch import FetchResult
from app.core.audit import verify_chain
from app.core.enums import BusinessStatus as S
from app.core.enums import Severity
from app.core.state_machine import advance  # noqa: F401  (kept for clarity of flow)
from app.models.audit import AuditEvent
from app.models.business import Business
from app.models.site_weakness import SiteWeakness
from app.stages.qualify import (
    SiteProber,
    is_franchise,
    opportunity_score,
    qualify,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 7, 29, tzinfo=UTC)
HEALTHY_HTML = (
    '<html><head><meta name="viewport" content="width=device-width">'
    "<title>Acme</title></head><body>© 2026 Acme</body></html>"
)


class FakeFetcher:
    """Deterministic fetcher: returns mapped results, else a 404."""

    def __init__(self, mapping: dict[str, FetchResult]) -> None:
        self.mapping = mapping

    def fetch(self, url: str) -> FetchResult:
        return self.mapping.get(
            url, FetchResult(ok=False, status=404, final_url=url, html="", elapsed_ms=0,
                             error="not found")
        )


def ok(url: str = "https://acme.com", html: str = HEALTHY_HTML, final: str | None = None,
       ms: int = 300) -> FetchResult:
    return FetchResult(ok=True, status=200, final_url=final or url, html=html, elapsed_ms=ms)


def prober(mapping: dict[str, FetchResult] | None = None) -> SiteProber:
    return SiteProber(FakeFetcher(mapping or {}), now=NOW)


def _business(session, *, name="Acme LLC", url=None) -> Business:
    biz = Business(name=name, location="Frisco, TX", existing_site_url=url,
                   status=S.DISCOVERED)
    session.add(biz)
    session.flush()
    return biz


# --------------------------- probing / weaknesses --------------------------- #
def test_no_site_flagged_high():
    has_site, findings = prober().assess(None)
    assert has_site is False
    assert [f.issue for f in findings] == ["no_site"]
    assert findings[0].severity is Severity.HIGH


def test_social_only_counts_as_no_site():
    has_site, findings = prober().assess("https://facebook.com/acmefrisco")
    assert has_site is False
    assert findings[0].issue == "no_site"


def test_unreachable_site_is_high_weakness():
    has_site, findings = prober({}).assess("https://dead.example")
    assert has_site is False
    assert findings[0].issue == "site_unreachable"
    assert findings[0].severity is Severity.HIGH


def test_healthy_site_has_no_weaknesses():
    url = "https://good.example"
    has_site, findings = prober({url: ok(url=url)}).assess(url)
    assert has_site is True
    assert findings == []


def test_detects_no_https():
    url = "http://insecure.example"
    has_site, findings = prober({url: ok(url=url, final="http://insecure.example")}).assess(url)
    assert has_site is True
    assert any(f.issue == "no_https" and f.severity is Severity.HIGH for f in findings)


def test_detects_missing_viewport():
    url = "https://noviewport.example"
    html = "<html><head><title>x</title></head><body>© 2026</body></html>"
    _, findings = prober({url: ok(url=url, html=html)}).assess(url)
    assert any(f.issue == "not_mobile_responsive" for f in findings)


def test_detects_stale_copyright():
    url = "https://stale.example"
    html = '<html><head><meta name="viewport"></head><body>© 2018 Old Co</body></html>'
    _, findings = prober({url: ok(url=url, html=html)}).assess(url)
    stale = [f for f in findings if f.issue == "stale_content"]
    assert stale and "2018" in (stale[0].evidence or "")


def test_detects_slow_load():
    url = "https://slow.example"
    _, findings = prober({url: ok(url=url, ms=6000)}).assess(url)
    assert any(f.issue == "slow_load" and f.severity is Severity.LOW for f in findings)


# ------------------------------- scoring ------------------------------------ #
def test_opportunity_score_monotonic():
    url = "http://bad.example"  # http + stale + no viewport
    html = "<html><head></head><body>© 2017</body></html>"
    _, many = prober({url: ok(url=url, final="http://bad.example", html=html)}).assess(url)
    _, few = prober({"https://ok.example": ok(url="https://ok.example")}).assess(
        "https://ok.example"
    )
    assert opportunity_score(many) > opportunity_score(few) == 0
    assert opportunity_score(many) <= 10


# ------------------------------- franchise ---------------------------------- #
def test_is_franchise():
    assert is_franchise("McDonald's #123")
    assert not is_franchise("Vinny's Corner Cafe")


# ------------------------- the Frisco finding, as a guard ------------------- #
def test_guard_site_presence_probed_not_trusted(session):
    """has_site reflects the actual probe, never the mere presence of a URL."""
    live = _business(session, url="https://live.example")
    dead = _business(session, url="https://dead.example")  # URL present but 404s
    p = prober({"https://live.example": ok(url="https://live.example")})

    qualify(session, live, p)
    qualify(session, dead, p)

    assert live.has_site is True  # reachable -> verified present
    assert dead.has_site is False  # URL claimed but unreachable -> not present
    assert dead.status is S.QUALIFIED  # a dead "site" is a lead


# --------------------------- spine integration ------------------------------ #
def test_qualify_no_site_advances_to_qualified_with_evidence(session):
    biz = _business(session, url=None)
    qualify(session, biz, prober())
    assert biz.status is S.QUALIFIED
    assert biz.has_site is False
    assert biz.opportunity_score == 3
    weaknesses = session.execute(select(SiteWeakness)).scalars().all()
    assert [w.issue for w in weaknesses] == ["no_site"]


def test_qualify_healthy_site_disqualified(session):
    url = "https://healthy.example"
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url)}))
    assert biz.status is S.DISQUALIFIED
    assert biz.has_site is True
    assert biz.opportunity_score == 0
    assert session.execute(select(func.count()).select_from(SiteWeakness)).scalar_one() == 0


def test_qualify_low_only_weakness_is_not_a_lead(session):
    # A site whose only issue is a slow load (LOW) must NOT be a lead — this is
    # the deterministic-qualification fix: transient latency can't flip a healthy
    # site to QUALIFIED. The weakness is still recorded as evidence.
    url = "https://slowbutfine.example"
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url, ms=9000)}))
    assert biz.status is S.DISQUALIFIED
    assert biz.has_site is True
    issues = [w.issue for w in session.execute(select(SiteWeakness)).scalars()]
    assert issues == ["slow_load"]  # recorded, but not lead-qualifying


def test_qualify_franchise_disqualified_without_probing(session):
    biz = _business(session, name="McDonald's Frisco", url="https://mcdonalds.com")
    qualify(session, biz, prober())  # empty fetcher; must not be consulted
    assert biz.status is S.DISQUALIFIED
    assert session.execute(select(func.count()).select_from(SiteWeakness)).scalar_one() == 0


def test_qualify_audit_chain_intact(session):
    biz = _business(session, url=None)
    qualify(session, biz, prober())
    ok_chain, bad = verify_chain(session)
    assert ok_chain is True and bad is None


# ---------------- heavy validation: determinism + the WHY reasons ----------- #
def _reason(session, biz) -> str:
    ev = session.execute(
        select(AuditEvent)
        .where(AuditEvent.subject_id == biz.id, AuditEvent.action.like("advance:%"))
        .order_by(AuditEvent.seq.desc())
        .limit(1)
    ).scalars().first()
    return (ev.after or {}).get("reason", "")


NO_VIEWPORT = "<html><head></head><body>© 2026</body></html>"  # MEDIUM: not_mobile_responsive


@pytest.mark.parametrize("ms", [200, 4001, 9000, 30000])
def test_healthy_site_disqualified_regardless_of_latency(session, ms):
    # The determinism guarantee: a healthy site never becomes a lead because a
    # single fetch was slow. Only the STATUS is asserted (slow_load may or may
    # not be recorded as evidence depending on ms).
    url = "https://healthy.example"
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url, ms=ms)}))
    assert biz.status is S.DISQUALIFIED


@pytest.mark.parametrize("ms", [200, 9000])
def test_weak_site_qualified_regardless_of_latency(session, ms):
    url = "http://weak.example"  # no_https (HIGH) — a structural problem
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url, final="http://weak.example", ms=ms)}))
    assert biz.status is S.QUALIFIED


def test_medium_only_weakness_qualifies(session):
    url = "https://noviewport.example"  # only not_mobile_responsive (MEDIUM)
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url, html=NO_VIEWPORT)}))
    assert biz.status is S.QUALIFIED


def test_status_is_always_binary(session):
    # Property: qualify always lands on exactly QUALIFIED or DISQUALIFIED.
    for url, resp in [
        (None, None),
        ("https://healthy.example", ok(url="https://healthy.example")),
        ("http://weak.example", ok(url="http://weak.example", final="http://weak.example")),
    ]:
        biz = _business(session, url=url)
        qualify(session, biz, prober({url: resp} if resp else {}))
        assert biz.status in (S.QUALIFIED, S.DISQUALIFIED)


def test_reason_no_site(session):
    biz = _business(session, url=None)
    qualify(session, biz, prober())
    assert _reason(session, biz) == "no website"


def test_reason_unreachable(session):
    biz = _business(session, url="https://dead.example")
    qualify(session, biz, prober({}))
    assert _reason(session, biz) == "site listed but does not load"


def test_reason_weak_site_lists_issues(session):
    url = "http://weak.example"  # no_https + stale + no viewport
    html = "<html><head></head><body>© 2017</body></html>"
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url, final="http://weak.example", html=html)}))
    reason = _reason(session, biz)
    assert reason.startswith("weak site:")
    assert "no_https" in reason


def test_reason_healthy(session):
    url = "https://healthy.example"
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url)}))
    assert _reason(session, biz) == "existing site is healthy"


def test_reason_low_only_names_the_signal(session):
    url = "https://slow.example"
    biz = _business(session, url=url)
    qualify(session, biz, prober({url: ok(url=url, ms=9000)}))
    reason = _reason(session, biz)
    assert "minor signals" in reason and "slow_load" in reason


def test_reason_franchise(session):
    biz = _business(session, name="McDonald's Frisco", url="https://mcdonalds.com")
    qualify(session, biz, prober())
    assert "chain/franchise" in _reason(session, biz)


def test_no_weakness_persisted_for_franchise(session):
    biz = _business(session, name="Starbucks Frisco", url="https://starbucks.com")
    qualify(session, biz, prober())
    assert session.execute(select(func.count()).select_from(SiteWeakness)).scalar_one() == 0
