"""Stage 2: QUALIFY.

Decide whether a discovered business is a lead. The core rule (a Frisco-run
finding): **site presence and quality are determined by independently probing the
live site — never by trusting the source's "has website" field.** A business the
directory listed as "Facebook only" may actually have a real site (→ not a lead),
and one it listed with a URL may be dead (→ a lead). We probe to find out.

Outcome:
- healthy, reachable site with no weaknesses -> DISQUALIFIED (already covered),
- no site / weak site (weaknesses found) -> QUALIFIED with an opportunity score,
- franchise/chain -> DISQUALIFIED (they don't buy from cold outreach).

All weaknesses are persisted as evidence and the transition is audited via the
spine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.adapters.site_fetch import SiteFetcher
from app.core.enums import Actor, BusinessStatus, Severity
from app.core.state_machine import advance
from app.models.business import Business
from app.models.site_weakness import SiteWeakness

# Hosts that are a social/aggregator presence, not a real owned website.
SOCIAL_HOSTS = frozenset(
    {
        "facebook.com", "m.facebook.com", "instagram.com", "linktr.ee",
        "linkedin.com", "yelp.com", "business.google.com", "sites.google.com",
    }
)

# Chains/franchises don't buy websites from cold outreach.
FRANCHISE_MARKERS = frozenset(
    {
        "mcdonald", "starbucks", "subway", "chick-fil-a", "chipotle", "domino",
        "pizza hut", "taco bell", "wendy", "burger king", "dunkin", "walmart",
        "7-eleven", "ihop", "applebee", "chili's",
    }
)

SEVERITY_WEIGHT = {Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3}
SLOW_LOAD_MS = 4000
STALE_YEARS = 2
_COPYRIGHT_YEAR = re.compile(r"(?:©|&copy;|copyright)[^\d]{0,12}(20\d{2})", re.IGNORECASE)


@dataclass(frozen=True)
class WeaknessFinding:
    issue: str
    severity: Severity
    evidence: str | None = None


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def is_social_or_absent(url: str | None) -> bool:
    return not url or _host(url) in SOCIAL_HOSTS


def is_franchise(name: str) -> bool:
    low = name.lower()
    return any(marker in low for marker in FRANCHISE_MARKERS)


class SiteProber:
    """Independently determines whether a real, reachable site exists and lists
    its weaknesses. Depends on a ``SiteFetcher`` so it is fully testable."""

    def __init__(self, fetcher: SiteFetcher, *, now: datetime | None = None) -> None:
        self._fetcher = fetcher
        self._now = now or datetime.now(UTC)

    def assess(self, url: str | None) -> tuple[bool, list[WeaknessFinding]]:
        if is_social_or_absent(url):
            return False, [
                WeaknessFinding(
                    "no_site", Severity.HIGH, f"no real website (source gave: {url or 'none'})"
                )
            ]

        result = self._fetcher.fetch(url)  # type: ignore[arg-type]
        if not result.ok:
            return False, [
                WeaknessFinding(
                    "site_unreachable",
                    Severity.HIGH,
                    f"claimed site did not load (status={result.status}, err={result.error})",
                )
            ]

        findings: list[WeaknessFinding] = []
        final = result.final_url or url or ""
        if not final.lower().startswith("https://"):
            findings.append(
                WeaknessFinding("no_https", Severity.HIGH, f"final URL not HTTPS: {final}")
            )

        html = result.html or ""
        low = html.lower()
        if 'name="viewport"' not in low and "name='viewport'" not in low:
            findings.append(
                WeaknessFinding(
                    "not_mobile_responsive", Severity.MEDIUM, "no <meta name=viewport> tag"
                )
            )

        years = [int(y) for y in _COPYRIGHT_YEAR.findall(html)]
        if years:
            newest = max(years)
            if newest <= self._now.year - STALE_YEARS:
                findings.append(
                    WeaknessFinding(
                        "stale_content", Severity.MEDIUM, f"copyright year {newest} (stale)"
                    )
                )

        if result.elapsed_ms > SLOW_LOAD_MS:
            findings.append(
                WeaknessFinding("slow_load", Severity.LOW, f"{result.elapsed_ms}ms load time")
            )

        return True, findings


def opportunity_score(findings: list[WeaknessFinding]) -> int:
    """0–10, monotonic in the number and severity of weaknesses."""
    return min(sum(SEVERITY_WEIGHT[f.severity] for f in findings), 10)


def qualify(session: Session, business: Business, prober: SiteProber) -> Business:
    """Probe, score, persist weaknesses, and advance the business via the spine."""
    if is_franchise(business.name):
        business.opportunity_score = 0
        advance(
            session, business, BusinessStatus.DISQUALIFIED,
            actor=Actor.SYSTEM.value, reason="franchise/chain",
        )
        return business

    has_site, findings = prober.assess(business.existing_site_url)
    business.has_site = has_site
    for f in findings:
        session.add(
            SiteWeakness(
                business_id=business.id, issue=f.issue, severity=f.severity, evidence=f.evidence
            )
        )
    session.flush()

    score = opportunity_score(findings)
    business.opportunity_score = score

    # Only structural problems (MEDIUM/HIGH) make a site a lead. A lone LOW signal
    # such as slow_load is recorded as evidence but is too noisy — a single slow
    # fetch over a variable network — to flip a healthy site into a target. This
    # keeps qualification deterministic across runs.
    qualifying = [f for f in findings if f.severity in (Severity.MEDIUM, Severity.HIGH)]
    if qualifying:
        advance(
            session, business, BusinessStatus.QUALIFIED,
            actor=Actor.SYSTEM.value, reason=f"opportunity_score={score}",
        )
    else:
        reason = (
            "existing site healthy — not a target"
            if not findings
            else "only low-severity signals — not a lead"
        )
        advance(
            session, business, BusinessStatus.DISQUALIFIED,
            actor=Actor.SYSTEM.value, reason=reason,
        )
    return business
