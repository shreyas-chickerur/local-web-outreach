"""Source collection for real (non-bundled) businesses.

Research needs *independent* sources to corroborate a fact. For a live lead we
have two we can stand behind:

1. the **Google Business Profile** record we discovered them from (name, address,
   phone), and
2. the business's **own website**, fetched directly.

Anything only one source asserts stays UNVERIFIED and becomes an owner question
— we never manufacture corroboration to make a page look more complete.

This module also scrapes the business's own public contact email, which is what
lets a real lead reach the email gate at all (Places does not return emails).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.adapters.site_fetch import HttpSiteFetcher
from app.ai.research_runner import RawClaim, SourceRecord
from app.core.enums import SourceType

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

# Addresses that are never a business owner's real inbox.
_EMAIL_BLOCKLIST = ("example.com", "sentry.io", "wixpress.com", "godaddy.com",
                    "squarespace.com", "@2x", ".png", ".jpg", ".webp")


def html_to_text(html: str) -> str:
    """Crude but dependency-free text extraction — enough to find contact info."""
    without_code = _TAG_RE.sub(" ", html or "")
    return re.sub(r"\s+", " ", _ANY_TAG_RE.sub(" ", without_code)).strip()


def find_contact_email(html: str) -> str | None:
    """The most plausible public contact address on the page, or None.

    Prefers role addresses an owner actually reads (info@, contact@, hello@)
    over whatever appears first.
    """
    candidates = []
    for match in _EMAIL_RE.findall(html or ""):
        addr = match.strip().lower()
        if any(bad in addr for bad in _EMAIL_BLOCKLIST):
            continue
        candidates.append(addr)
    if not candidates:
        return None
    preferred = ("info@", "contact@", "hello@", "office@", "sales@")
    for pref in preferred:
        for addr in candidates:
            if addr.startswith(pref):
                return addr
    return candidates[0]


def find_phone(text: str) -> str | None:
    match = _PHONE_RE.search(text or "")
    return match.group(0).strip() if match else None


@dataclass
class Collected:
    sources: list[SourceRecord]
    contact_email: str | None


def collect_sources(business, fetcher: HttpSiteFetcher | None = None) -> Collected:  # noqa: ANN001
    """Collect the sources we can defend for one discovered business."""
    sources: list[SourceRecord] = []

    # Source 1 — the Google Business Profile record behind the discovery.
    gbp_url = (
        f"https://www.google.com/maps/place/?q=place_id:{business.place_id}"
        if business.place_id else "https://www.google.com/maps"
    )
    gbp_claims = []
    if business.address:
        gbp_claims.append(RawClaim(field="address", value=business.address,
                                   source_url=gbp_url, source_type=SourceType.GBP))
    if business.phone:
        gbp_claims.append(RawClaim(field="phone", value=business.phone,
                                   source_url=gbp_url, source_type=SourceType.GBP))
    sources.append(SourceRecord(
        source_type=SourceType.GBP, source_url=gbp_url, entity_name=business.name,
        entity_address=business.address, entity_phone=business.phone, claims=gbp_claims,
    ))

    # Source 2 — the business's own website (independent of the directory).
    contact_email = None
    if business.existing_site_url:
        result = (fetcher or HttpSiteFetcher()).fetch(business.existing_site_url)
        if result.ok and result.html:
            text = html_to_text(result.html)
            contact_email = find_contact_email(result.html)
            site_claims = []
            phone = find_phone(text)
            if phone:
                site_claims.append(RawClaim(
                    field="phone", value=phone,
                    source_url=result.final_url or business.existing_site_url,
                    source_type=SourceType.EXISTING_SITE,
                ))
            sources.append(SourceRecord(
                source_type=SourceType.EXISTING_SITE,
                source_url=result.final_url or business.existing_site_url,
                entity_name=business.name, entity_address=business.address,
                entity_phone=phone, raw_text=text[:20000], claims=site_claims,
            ))

    return Collected(sources=sources, contact_email=contact_email)
