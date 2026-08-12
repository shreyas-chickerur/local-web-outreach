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

from app.adapters.directory import DirectorySource
from app.adapters.site_fetch import HttpSiteFetcher
from app.ai.research_runner import RawClaim, SourceRecord
from app.core.enums import SourceType
from app.stages.extract_site import ExtractedSite, extract_from_html, merge

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


# Owners publish their address on a contact page far more often than on the
# homepage, so follow the obvious ones rather than giving up after one fetch.
_CONTACT_PATHS = ("contact", "contact-us", "about", "about-us", "get-a-quote", "estimate")
_CONTACT_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def contact_page_urls(html: str, base_url: str, limit: int = 3) -> list[str]:
    """Absolute URLs of likely contact/about pages linked from ``html``."""
    from urllib.parse import urljoin, urlparse

    base_host = urlparse(base_url).netloc.lower()
    found: list[str] = []
    for href in _CONTACT_LINK_RE.findall(html or ""):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc.lower() != base_host:  # stay on their own site
            continue
        path = parsed.path.strip("/").lower()
        if not path:
            continue
        last = path.split("/")[-1]
        if any(last == c or last.startswith(c) for c in _CONTACT_PATHS):
            if absolute not in found:
                found.append(absolute)
        if len(found) >= limit:
            break
    return found


# A directory's category titles describe what the business *is*. For food we want
# "South Indian Restaurant", not a list of dishes; for trades, "Landscaping".
_BASE_NOUNS = {
    "restaurants": "Restaurant", "food": "Restaurant", "fast food": "Fast Food",
    "cafes": "Cafe", "coffee & tea": "Cafe", "bakeries": "Bakery", "bars": "Bar",
    "food trucks": "Food Truck", "delis": "Deli", "pizza": "Pizza Restaurant",
}
# Titles that are a venue type rather than a cuisine/speciality.
_GENERIC_TITLES = {"restaurants", "food", "fast food", "cafes", "coffee & tea",
                   "bakeries", "bars", "food trucks", "delis", "breakfast & brunch"}


_FOOD_CATEGORIES = {"restaurant", "cafe", "diner", "bakery", "bar", "food"}
# Titles that already name a venue, so appending "Restaurant" would read wrong
# ("Steakhouses Restaurant").
_VENUE_NOUNS = ("restaurant", "cafe", "bar", "bakery", "grill", "house", "pizzeria",
                "diner", "deli", "pub", "kitchen", "buffet", "bbq", "steakhouse",
                "creamery", "parlor", "lounge", "bistro", "brasserie", "taqueria")


def service_label(categories: tuple[str, ...] | list[str],
                  category_hint: str | None = None) -> str | None:
    """Turn directory category titles into one human label.

    ``("Indian", "Fast Food")`` -> ``"Indian Fast Food"``; ``("Greek",)`` for a
    restaurant -> ``"Greek Restaurant"``; ``("Landscaping", "Lawn Services")`` ->
    ``"Landscaping"``. Returns None when there is nothing to say — we never
    invent a description.
    """
    titles = [t.strip() for t in (categories or []) if t and t.strip()]
    if not titles:
        return None
    speciality = [t for t in titles if t.lower() not in _GENERIC_TITLES]
    generic = [t for t in titles if t.lower() in _GENERIC_TITLES]
    if speciality and generic:
        return f"{speciality[0]} {_BASE_NOUNS.get(generic[0].lower(), generic[0])}"
    if speciality:
        label = speciality[0]
        # A bare cuisine ("Greek") reads as an adjective; name the venue type.
        if (category_hint or "").lower() in _FOOD_CATEGORIES and not any(
            noun in label.lower() for noun in _VENUE_NOUNS
        ):
            return f"{label} Restaurant"
        return label
    return _BASE_NOUNS.get(generic[0].lower(), generic[0])


def tidy_address(address: str | None) -> str | None:
    """Drop the trailing country on a display address (Google appends ', USA')."""
    if not address:
        return address
    text = address.strip()
    for suffix in (", USA", ", United States", ", US"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text.strip().rstrip(",")


@dataclass
class Collected:
    sources: list[SourceRecord]
    contact_email: str | None
    # Their own site's content — self-attested, carried into the proposal so it
    # is a real website rather than a business card.
    extracted: ExtractedSite | None = None


def collect_sources(
    business,  # noqa: ANN001
    fetcher: HttpSiteFetcher | None = None,
    directories: list[DirectorySource] | None = None,
) -> Collected:
    """Collect the sources we can defend for one discovered business."""
    sources: list[SourceRecord] = []

    # Source 1 — the Google Business Profile record behind the discovery.
    gbp_url = (
        f"https://www.google.com/maps/place/?q=place_id:{business.place_id}"
        if business.place_id else "https://www.google.com/maps"
    )
    gbp_claims = []
    if business.address:
        gbp_claims.append(RawClaim(field="address", value=tidy_address(business.address) or "",
                                   source_url=gbp_url, source_type=SourceType.GBP))
    if business.phone:
        gbp_claims.append(RawClaim(field="phone", value=business.phone,
                                   source_url=gbp_url, source_type=SourceType.GBP))
    if getattr(business, "rating", None):
        gbp_claims.append(RawClaim(field="rating", value=str(business.rating),
                                   source_url=gbp_url, source_type=SourceType.GBP))
    sources.append(SourceRecord(
        source_type=SourceType.GBP, source_url=gbp_url, entity_name=business.name,
        entity_address=business.address, entity_phone=business.phone, claims=gbp_claims,
    ))

    # Sources 2..n — third-party directories (OSM, Yelp). Independent of Google,
    # so they can actually corroborate; without them a business with no website
    # has a single source and every fact stays UNVERIFIED forever.
    directory_labels: list[tuple[str, str]] = []
    for directory in (directories or []):
        place = directory.lookup(business.name, business.location)
        if place is None:
            continue
        dir_claims = []
        if place.address:
            dir_claims.append(RawClaim(field="address", value=tidy_address(place.address) or "",
                                       source_url=place.source_url,
                                       source_type=SourceType.DIRECTORY))
        if place.phone:
            dir_claims.append(RawClaim(field="phone", value=place.phone,
                                       source_url=place.source_url,
                                       source_type=SourceType.DIRECTORY))
        if place.rating:
            # A second platform's rating corroborates Google's. They agree only
            # loosely, so corroborate() compares ratings to the nearest half star.
            dir_claims.append(RawClaim(field="rating", value=str(place.rating),
                                       source_url=place.source_url,
                                       source_type=SourceType.DIRECTORY))
        label = service_label(place.categories, getattr(business, 'category', None))
        if label:
            dir_claims.append(RawClaim(field="services", value=label,
                                       source_url=place.source_url,
                                       source_type=SourceType.DIRECTORY))
            directory_labels.append((label, place.source_url))
        if dir_claims:
            sources.append(SourceRecord(
                source_type=SourceType.DIRECTORY, source_url=place.source_url,
                entity_name=place.name, entity_address=place.address,
                entity_phone=place.phone, claims=dir_claims,
            ))

    # Final source — the business's own website (independent of the directories).
    contact_email = None
    extracted: ExtractedSite | None = None
    if business.existing_site_url:
        result = (fetcher or HttpSiteFetcher()).fetch(business.existing_site_url)
        if result.ok and result.html:
            text = html_to_text(result.html)
            base = result.final_url or business.existing_site_url
            contact_email = find_contact_email(result.html)
            extracted = extract_from_html(result.html, base)
            # Their contact/about pages carry the email and often the hours.
            for page in contact_page_urls(result.html, base):
                sub = (fetcher or HttpSiteFetcher()).fetch(page)
                if sub.ok and sub.html:
                    extracted = merge(extracted, extract_from_html(sub.html, page))
                    if contact_email is None:
                        contact_email = find_contact_email(sub.html)
            site_claims = []
            lowered = text.lower()
            for label, _ in directory_labels:
                # Their own site saying the same thing is genuine, independent
                # corroboration — not us echoing the directory back at itself.
                if all(word in lowered for word in label.lower().split()):
                    site_claims.append(RawClaim(
                        field="services", value=label,
                        source_url=result.final_url or business.existing_site_url,
                        source_type=SourceType.EXISTING_SITE,
                    ))
                    break
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

    return Collected(sources=sources, contact_email=contact_email, extracted=extracted)
