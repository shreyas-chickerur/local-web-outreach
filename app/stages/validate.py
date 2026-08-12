"""Independent re-validation of what the pipeline produced.

Research corroborates facts *at collection time*. This module re-checks them
**against the live sources, later** — a different question, and the one that
matters before anything is sent. It is deliberately adversarial: it tries to
prove each claim wrong, and reports what it could not confirm.

Nothing here mutates state. It answers "is this still true, and is the pitch
honest?" so the operator's review is about judgement, not fact-checking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.adapters.directory import DirectorySource
from app.adapters.site_fetch import HttpSiteFetcher
from app.core.enums import ClaimStatus
from app.models.business import Business
from app.models.research_claim import ResearchClaim
from app.models.site_weakness import SiteWeakness
from app.models.website import Website
from app.stages.entity_resolution import _name_similarity
from app.stages.research import _norm_value

RATING_TOLERANCE = 0.5
# A directory search returns its best guess, which may be a different business
# entirely — two Frisco roofers both "matched" one unrelated Yelp listing, whose
# phone then looked like proof our stored phone was wrong. Compare facts only
# when the matched record is plausibly the same entity.
NAME_MATCH_THRESHOLD = 0.6


@dataclass
class Finding:
    level: str  # "ok" | "warn" | "fail"
    check: str
    detail: str


@dataclass
class BusinessReport:
    business_id: object
    name: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def failed(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "fail"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warn"]

    @property
    def sendable(self) -> bool:
        """A lead is sendable only if nothing failed outright."""
        return not self.failed


def _claims(session, business_id) -> list[ResearchClaim]:  # noqa: ANN001
    return session.query(ResearchClaim).filter_by(business_id=business_id).all()


def check_claims_against_live_sources(
    business: Business, claims: list[ResearchClaim], directories: list[DirectorySource]
) -> list[Finding]:
    """Re-query each directory and compare it to what we stored."""
    findings: list[Finding] = []
    live: dict[str, str] = {}
    mismatched: list[str] = []
    for directory in directories:
        place = directory.lookup(business.name, business.location)
        if place is None:
            continue
        if _name_similarity(business.name, place.name) < NAME_MATCH_THRESHOLD:
            mismatched.append(f"{getattr(directory, 'name', 'directory')}: {place.name!r}")
            continue
        if place.address and "address" not in live:
            live["address"] = place.address
        if place.phone and "phone" not in live:
            live["phone"] = place.phone
        if place.rating and "rating" not in live:
            live["rating"] = str(place.rating)

    for note in mismatched:
        findings.append(Finding(
            "warn", "entity-match",
            f"ignored a directory hit for a different business ({note})"))

    verified = [c for c in claims if c.status is ClaimStatus.VERIFIED]
    if not verified:
        findings.append(Finding("warn", "verified-facts",
                                "no VERIFIED facts — the proposal will look empty"))
    for claim in verified:
        current = live.get(claim.field)
        stored = claim.value or ""
        if current is None or not stored:
            findings.append(Finding(
                "warn", f"recheck:{claim.field}",
                f"could not re-confirm {claim.field} live (directory returned nothing)"))
            continue
        if claim.field == "rating":
            try:
                agrees = abs(float(stored) - float(current)) <= RATING_TOLERANCE
            except (TypeError, ValueError):
                agrees = False
        else:
            agrees = _norm_value(stored, claim.field) == _norm_value(current, claim.field)
        findings.append(Finding(
            "ok" if agrees else "fail", f"recheck:{claim.field}",
            f"stored {stored!r} vs live {current!r}"))
    return findings


def check_weaknesses_are_real(
    business: Business, weaknesses: list[SiteWeakness], fetcher: HttpSiteFetcher
) -> list[Finding]:
    """The pitch rests on the weakness being true *now*. Prove it again."""
    findings: list[Finding] = []
    if not business.existing_site_url:
        if any(w.issue == "no_site" for w in weaknesses):
            findings.append(Finding("ok", "weakness:no_site", "no website on record"))
        return findings

    result = fetcher.fetch(business.existing_site_url)
    final = (result.final_url or "") if result else ""
    for weakness in weaknesses:
        if weakness.issue in {"site_unreachable"}:
            level = "ok" if not result.ok else "fail"
            findings.append(Finding(
                level, "weakness:site_unreachable",
                f"site {'still down' if not result.ok else 'is UP now — pitch is stale'}"))
        elif weakness.issue == "no_https":
            level = "ok" if not final.startswith("https") else "fail"
            findings.append(Finding(
                level, "weakness:no_https",
                f"final URL {final or 'n/a'}"
                + ("" if level == "ok" else " — they have HTTPS now, pitch is stale")))
        elif weakness.issue == "not_mobile_responsive":
            has_viewport = "name=\"viewport\"" in (result.html or "").lower() or \
                           "name='viewport'" in (result.html or "").lower()
            findings.append(Finding(
                "ok" if not has_viewport else "fail", "weakness:not_mobile_responsive",
                "no viewport tag" if not has_viewport else "viewport present — pitch is stale"))
    return findings


def check_outreach_readiness(business: Business, site: Website | None) -> list[Finding]:
    """Everything that must be true before this lead can produce an email."""
    findings: list[Finding] = []
    if site is None:
        findings.append(Finding("fail", "site-draft", "no site draft"))
    if not business.contact_email:
        findings.append(Finding(
            "warn", "contact-email",
            "no contact email found — this lead cannot reach the email gate"))
    return findings


def validate_business(
    session,  # noqa: ANN001
    business: Business,
    *,
    directories: list[DirectorySource],
    fetcher: HttpSiteFetcher,
) -> BusinessReport:
    report = BusinessReport(business_id=business.id, name=business.name)
    claims = _claims(session, business.id)
    weaknesses = session.query(SiteWeakness).filter_by(business_id=business.id).all()
    site = (session.query(Website).filter_by(business_id=business.id)
            .order_by(Website.version.desc()).first())

    report.findings += check_claims_against_live_sources(business, claims, directories)
    report.findings += check_weaknesses_are_real(business, weaknesses, fetcher)
    report.findings += check_outreach_readiness(business, site)
    return report
