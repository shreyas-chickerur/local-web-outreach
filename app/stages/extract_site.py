"""Read a business's existing website and pull out what a new site must carry.

A proposal that shows only name, phone and address is a business card, not a
website. What makes it credible is *their own content*: the services they sell,
their hours, how they describe themselves, and the actions their customers came
to perform (order, book, get a quote).

Provenance matters. A fact from a third-party directory needs corroboration
before we present it as true — that's the research invariant. Content taken from
the business's **own** website is different in kind: it is self-attested, the
business published it about itself. Rendering it is not fabrication, it is
carrying their content across. It is tagged ``self_attested`` throughout so the
operator always sees which is which.

Deliberately dependency-free (regex over HTML): the input is untrusted third-party
markup, and every extracted value is escaped at render time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from urllib.parse import urljoin, urlparse

_TAG_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)
_HEADING_RE = re.compile(r"<h([1-3])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL)
_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                      re.IGNORECASE | re.DOTALL)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)

_DAYS = r"(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*"
_HOURS_RE = re.compile(
    rf"{_DAYS}(?:\s*[-–—]\s*{_DAYS})?\s*[:\-–—]?\s*"
    r"(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[-–—to]+\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)|closed)",
    re.IGNORECASE)

_SOCIAL_HOSTS = {
    "facebook.com": "Facebook", "instagram.com": "Instagram", "twitter.com": "X",
    "x.com": "X", "yelp.com": "Yelp", "linkedin.com": "LinkedIn",
    "tiktok.com": "TikTok", "youtube.com": "YouTube",
}

# The things a visitor actually came to do. A new site that drops these is a
# downgrade no matter how it looks.
_ACTION_PATTERNS = (
    (("order online", "order now", "start order", "place an order"), "Order Online"),
    (("book", "reserve", "reservation", "appointment", "schedule"), "Book / Reserve"),
    (("quote", "estimate", "consultation"), "Get a Quote"),
    (("menu",), "Menu"),
    (("shop", "store", "buy"), "Shop"),
    (("gallery", "portfolio", "our work"), "Gallery"),
    (("careers", "apply", "hiring"), "Careers"),
)

_NAV_NOISE = {"home", "contact", "contact us", "about", "about us", "privacy",
              "privacy policy", "terms", "sitemap", "search", "login", "log in",
              "sign up", "cart", "blog", "news", "faq", "faqs", "services",
              "our services", "how it works", "disclaimer", "philosophy",
              "events", "gallery", "careers", "reviews", "testimonials",
              "our team", "team", "hours", "location", "locations", "menu",
              "a few of our partners", "partners", "follow us", "newsletter",
              "visit us", "find us", "get in touch", "order online", "book now",
              "read more", "learn more", "see more", "view all", "shop now"}

# Awards and press are social proof. Even when the business published them, they
# must not be silently re-presented as an offering — invariant #1 forbids
# fabricated social proof, and "Nominated for Best Chef" is not a service.
_SOCIAL_PROOF_RE = re.compile(
    r"\b(award\w*|nominat\w*|winner|winning|voted|rated|acclaim\w*|"
    r"best of|best chef|top \d|featured in|as seen|press|michelin|james beard|"
    r"\d+\s*stars?)\b",
    re.IGNORECASE)


# Registrar / parking / builder hosts: a link here is not a real customer action.
# Images that are not photographs of the business: logos, icons, and — important
# for invariant #1 — award/press badges. An award badge as the hero is both ugly
# and a social-proof claim we must not re-present.
_JUNK_IMAGE_RE = re.compile(
    r"(logo|badge|award|seal|icon|favicon|sprite|placeholder|spacer|pixel|"
    r"beard|semifinalist|finalist|winner|rating|stars?|yelp|tripadvisor|"
    r"facebook|instagram|arrow|chevron|btn|button)", re.IGNORECASE)

_JUNK_ACTION_HOSTS = ("godaddy.com", "wix.com", "squarespace.com", "weebly.com",
                      "namecheap.com", "domain.com", "wordpress.com", "shopify.com")

# Booking providers a real business legitimately sends customers to.
_ALLOWED_ACTION_HOSTS = ("opentable.com", "resy.com", "toasttab.com", "square.site",
                         "doordash.com", "ubereats.com", "grubhub.com", "calendly.com",
                         "housecallpro.com", "acuityscheduling.com", "booksy.com",
                         "yelp.com", "clover.com", "chownow.com", "olo.com")


def _text(fragment: str) -> str:
    """Strip tags/entities from an HTML fragment and collapse whitespace."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


@dataclass
class ExtractedSite:
    """What their current website says about them. All self-attested."""

    title: str | None = None
    description: str | None = None
    about: str | None = None
    services: list[str] = field(default_factory=list)
    hours: list[str] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)   # {label, url, kind}
    socials: list[dict] = field(default_factory=list)   # {name, url}
    images: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any((self.about, self.services, self.hours, self.actions, self.images))


def _clean_service(candidate: str) -> str | None:
    text = _text(candidate)
    if not (3 <= len(text) <= 60):
        return None
    if text.lower() in _NAV_NOISE:
        return None
    if text.count(" ") > 7:          # a sentence, not a service name
        return None
    if re.search(r"(https?://|@|\d{3}[-.\s]\d{4})", text):
        return None
    if _SOCIAL_PROOF_RE.search(text):     # awards/press are not offerings
        return None
    return text


def _action_allowed(absolute: str, base_host: str) -> bool:
    """Keep actions that stay on their site or use a real booking provider."""
    host = urlparse(absolute).netloc.lower().replace("www.", "")
    if absolute.startswith("tel:") or absolute.startswith("mailto:"):
        return True
    if not host:
        return False
    if any(host.endswith(j) for j in _JUNK_ACTION_HOSTS):
        return False
    return host.endswith(base_host) or any(host.endswith(a) for a in _ALLOWED_ACTION_HOSTS)


def extract_from_html(html: str, base_url: str) -> ExtractedSite:
    """Pull the content and functionality out of one page of their site."""
    out = ExtractedSite()
    if not html:
        return out
    clean = _TAG_RE.sub(" ", html)

    title = _TITLE_RE.search(clean)
    if title:
        out.title = _text(title.group(1))[:200] or None
    desc = _META_DESC_RE.search(clean)
    if desc:
        out.description = _text(desc.group(1))[:300] or None

    # The longest paragraph is nearly always the "about" blurb.
    paragraphs = [_text(p) for p in _P_RE.findall(clean)]
    candidates = [p for p in paragraphs if 80 <= len(p) <= 600]
    if candidates:
        out.about = max(candidates, key=len)

    # Services: sub-headings and list items read as offerings.
    seen: set[str] = set()
    for level, fragment in _HEADING_RE.findall(clean):
        if level == "1":
            continue
        name = _clean_service(fragment)
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.services.append(name)
    for fragment in _LI_RE.findall(clean):
        if len(out.services) >= 12:
            break
        name = _clean_service(fragment)
        if name and name.lower() not in seen and " " in name:
            seen.add(name.lower())
            out.services.append(name)
    out.services = out.services[:12]

    page_text = _text(clean)
    out.hours = list(dict.fromkeys(m.group(0).strip() for m in _HOURS_RE.finditer(page_text)))[:7]

    base_host = urlparse(base_url).netloc.lower().replace("www.", "")
    action_seen: set[str] = set()
    for href, label_html in _LINK_RE.findall(clean):
        label = _text(label_html)
        if not label or href.startswith(("#", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        host = urlparse(absolute).netloc.lower().replace("www.", "")

        for social_host, name in _SOCIAL_HOSTS.items():
            if host.endswith(social_host) and name not in {s["name"] for s in out.socials}:
                out.socials.append({"name": name, "url": absolute})
                break
        else:
            lowered = label.lower()
            for needles, kind in _ACTION_PATTERNS:
                if any(n in lowered for n in needles) and kind not in action_seen:
                    if not _action_allowed(absolute, base_host):
                        break
                    action_seen.add(kind)
                    out.actions.append({"label": label[:40], "url": absolute, "kind": kind})
                    break

    for src in _IMG_RE.findall(clean):
        absolute = urljoin(base_url, src)
        if _JUNK_IMAGE_RE.search(absolute):   # logos, icons, award badges
            continue
        if re.search(r"\.(png|jpe?g|webp|avif)(\?|$)", absolute, re.IGNORECASE):
            if urlparse(absolute).netloc.lower().replace("www.", "").endswith(base_host):
                if absolute not in out.images:
                    out.images.append(absolute)
        if len(out.images) >= 8:
            break
    og = _OG_IMAGE_RE.search(clean)
    if og:
        hero = urljoin(base_url, _text(og.group(1)))
        # og:image is often the logo or an award badge — only promote a real photo.
        if not _JUNK_IMAGE_RE.search(hero):
            out.images = [hero] + [i for i in out.images if i != hero]

    return out


def merge(primary: ExtractedSite, extra: ExtractedSite) -> ExtractedSite:
    """Fold a secondary page (contact/about) into the homepage's extraction."""
    primary.about = primary.about or extra.about
    primary.description = primary.description or extra.description
    for svc in extra.services:
        if svc.lower() not in {s.lower() for s in primary.services} and len(primary.services) < 12:
            primary.services.append(svc)
    for hour in extra.hours:
        if hour not in primary.hours and len(primary.hours) < 7:
            primary.hours.append(hour)
    for action in extra.actions:
        if action["kind"] not in {a["kind"] for a in primary.actions}:
            primary.actions.append(action)
    for social in extra.socials:
        if social["name"] not in {s["name"] for s in primary.socials}:
            primary.socials.append(social)
    for image in extra.images:
        if image not in primary.images and len(primary.images) < 8:
            primary.images.append(image)
    return primary
