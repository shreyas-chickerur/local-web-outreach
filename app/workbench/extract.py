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

import json
import re
from dataclasses import dataclass, field
from html import unescape
from urllib.parse import urljoin, urlparse

_TAG_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
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
_ANY_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

_DAYS = r"(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*"
_HOURS_RE = re.compile(
    rf"{_DAYS}(?:\s*[-–—]\s*{_DAYS})?\s*[:\-–—]?\s*"
    r"(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[-–—to]+\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)|closed)",
    re.IGNORECASE)

# Menu / price-list parsing. A proposal that links back to the old site for the
# menu is not a replacement — the new page has to carry the food itself.
_MENU_PATHS = ("menu", "menus", "food", "drinks", "dinner", "lunch", "brunch",
               "breakfast", "pricing", "prices", "our-services", "services")
_PRICE_RE = re.compile(r"\$\s?\d{1,4}(?:\.\d{2})?")
_BLOCK_RE = re.compile(
    r"</?(p|div|li|tr|td|th|h[1-6]|section|article|br|ul|ol|dl|dt|dd)[^>]*>",
    re.IGNORECASE)


def html_to_lines(html: str) -> list[str]:
    """Text lines, keeping block boundaries so menu rows stay separate."""
    without_code = _TAG_RE.sub(" ", html or "")
    with_breaks = _BLOCK_RE.sub("\n", without_code)
    plain = unescape(re.sub(r"<[^>]+>", " ", with_breaks))
    return [re.sub(r"[ \t]+", " ", ln).strip() for ln in plain.split("\n") if ln.strip()]


def extract_menu_items(html: str) -> list[dict]:
    """Dishes / priced services: {name, price, description}.

    Anchored on the price, because a price is the one unambiguous signal that a
    line is an item for sale rather than prose or navigation.
    """
    items: list[dict] = []
    seen: set[str] = set()
    lines = html_to_lines(html)
    for i, line in enumerate(lines):
        match = _PRICE_RE.search(line)
        if not match or len(line) > 220:
            continue
        price = match.group(0).replace(" ", "")
        name = line[: match.start()].strip(" .-–—$\u2022|")
        description = line[match.end():].strip(" .-–—|")
        if not name and i:                       # price on its own line
            name = lines[i - 1].strip(" .-–—|")
        if not (2 < len(name) <= 70) or name.lower() in _NAV_NOISE:
            continue
        if _PRICE_RE.search(name) or name.lower() in seen:
            continue
        if not re.search(r"[A-Za-z]{3}", name):
            continue
        seen.add(name.lower())
        items.append({"name": name, "price": price,
                      "description": description[:160] if len(description) > 3 else ""})
        if len(items) >= 24:
            break
    return items


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
    # Retail goods, kept apart from services: both matter when building a site,
    # but calling a bottle of sauce a "service" makes the brief wrong.
    products: list[str] = field(default_factory=list)
    hours: list[str] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)   # {label, url, kind}
    socials: list[dict] = field(default_factory=list)   # {name, url}
    images: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    site_host: str = ""
    menu_items: list[dict] = field(default_factory=list)
    # Restaurants very often publish the menu as a PDF or photo. Embedding it
    # keeps the visitor on the new page; linking out defeats the replacement.
    menu_media: list[dict] = field(default_factory=list)   # {url, kind, label}
    # A dedicated locations page is the clearest sign of more than one branch.
    has_locations_page: bool = False
    # A business publishing its own phone and address is an independent source:
    # it is what lets a directory's claim reach two-source confirmation.
    phone: str | None = None
    address: str | None = None
    # Two things about a site that decide whether it needs replacing, both free
    # from HTML we already have: a page with no viewport meta tag was never
    # made responsive, and a site still on plain http is one browsers now warn
    # visitors about.
    mobile_ready: bool = True
    https: bool = True
    # The page draws itself with JavaScript, so the HTML we received is a shell.
    # Not knowing what is on a site is different from the site being empty, and
    # the difference matters: one is a lead, the other is our blind spot.
    js_rendered: bool = False
    # Visible words on the page. "Thin" has to mean the page is thin, not that
    # our heading filters found nothing they liked — a 336KB roofing site with
    # no parseable services is a failure of this reader, not a sales lead.
    text_words: int = 0

    def is_empty(self) -> bool:
        return not any((self.about, self.services, self.products, self.hours, self.actions,
                        self.images, self.menu_items))


def _hours_key(text: str) -> str:
    """'Mon-Fri 8am-5pm' and 'Mon-Fri 8:00am - 5:00pm' are the same entry."""
    lowered = re.sub(r"[^a-z0-9]", "", (text or "").lower())
    return re.sub(r"(\d)00", r"\1", lowered)      # 800am -> 8am


def _dedupe_hours(values) -> list[str]:  # noqa: ANN001
    seen: dict[str, str] = {}
    for value in values:
        key = _hours_key(value)
        # Keep the longest spelling — it is the one with the most information.
        if key not in seen or len(value) > len(seen[key]):
            seen[key] = value
    return list(seen.values())


# Headlines sell; they do not name an offering. "What We Do Best" and "Enjoy a
# Weed Free Lawn" are copy, and listing them as services makes the brief noise.
_MARKETING_RE = re.compile(
    r"^(what we|why |how we|enjoy |get |our commitment|welcome|discover |"
    r"experience |let us|we[''‘’]?re |we (are|offer|provide|believe)|"
    r"the .* difference)|[?!]$", re.IGNORECASE)

# Navigation and chrome, matched as SUBSTRINGS. An exact-match list missed
# every real variant: "Skip to content MENU", "LOCATIONS PLANO", "GIFT CARDS".
_CHROME_RE = re.compile(
    r"(skip to|gift card|locations?\b|donation|franchis|sign ?up|log ?in|newsletter|social|"
    r"subscribe|follow us|main menu|toggle|navigation|search|cart|checkout|"
    r"privacy|terms|accessibility|site ?map|upcoming events|nationwide|"
    r"shipping|directions)", re.IGNORECASE)

# Headings that structure a page rather than name something they sell:
# "What Our Clients Say", "Frequently Asked Questions", "Lawn Care Tips".
_SECTION_RE = re.compile(
    r"(clients? say|testimonial|what (our|people)|frequently asked|faq\b|"
    r"\btips?\b|\bguides?\b|walkthrough|our story|why choose|get a (free )?quote|"
    r"read more|learn more|latest|blog|gallery|portfolio)", re.IGNORECASE)

# Things they SELL rather than things they DO. For a barbecue joint the bottled
# sauce is real revenue, but it is not a service and should not be listed as one.
_PRODUCT_RE = re.compile(
    r"\b(sauce|seasoning|rub|spice|blend|jerky|bottle|jar|gift ?(set|box)|"
    r"bundle|sampler|pack)\b", re.IGNORECASE)

# An offering is a noun phrase ("Weed Control"). Filtering junk pattern by
# pattern was endless, so test the shape instead: a call to action starts with a
# verb aimed at the reader, and copy addresses them directly.
_CTA_RE = re.compile(
    r"^(talk|call|contact|book|schedule|request|order|shop|visit|find|see|"
    r"learn|discover|save|conserve|explore|start|join|get|ready|need)\b",
    re.IGNORECASE)
_ADDRESSES_READER_RE = re.compile(r"\b(we|us|our|you|your|i|my)\b", re.IGNORECASE)

# A heading is not necessarily an offering. "Mckinney, Texas" is where they are.
_PLACE_RE = re.compile(r"^[A-Za-z .'-]+,\s*(?:[A-Z]{2}|[A-Z][a-z]+)\s*\d{0,5}$")

# A footer row of social links, scraped as a single heading:
# "Instagram Facebook TikTok Yelp Google Reviews About".
_SOCIAL_PILE_RE = re.compile(
    r"(instagram|facebook|tiktok|twitter|yelp|youtube|linkedin)", re.IGNORECASE)

# Things a shop sells that are not services. A t-shirt is not an offering you
# would build a website section around.
_MERCH_RE = re.compile(
    r"\b(tee|t-shirt|shirt|hoodie|cap|hat|mug|sticker|merch\w*|gift set|"
    r"apparel|koozie|tumbler)\b", re.IGNORECASE)


# Without this tag a phone renders the desktop layout scaled down, which is
# what "their site looks broken on my phone" actually means.
_VIEWPORT_RE = re.compile(r'<meta[^>]+name=["\']viewport', re.IGNORECASE)
# The mount points the common frameworks leave in an otherwise empty document.
_SPA_RE = re.compile(
    r'(id=["\'](root|app|__next|__nuxt)["\']|window\.__NUXT__|__NEXT_DATA__)',
    re.IGNORECASE)
_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL)
_TEL_HREF_RE = re.compile(r'href=["\']tel:([^"\']+)["\']', re.IGNORECASE)
_PHONE_SHAPE_RE = re.compile(r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
_DAY_RE = re.compile(r"^(mo|tu|we|th|fr|sa|su)", re.IGNORECASE)


def _ld_nodes(html: str):
    """Every schema.org node on the page, however it is nested.

    Sites wrap their business record in @graph, in a list, or in neither, so
    walk whatever shape comes back rather than assuming one.
    """
    for block in _LD_RE.findall(html):
        try:
            data = json.loads(unescape(block.strip()))
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                yield node
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)


def _ld_address(node: dict) -> str | None:
    """A schema.org PostalAddress, flattened the way a directory writes it."""
    address = node.get("address")
    if isinstance(address, str):
        return _text(address) or None
    if not isinstance(address, dict):
        return None
    raw = [address.get(k) for k in
           ("streetAddress", "addressLocality", "addressRegion", "postalCode")]
    parts = [_text(str(v)) for v in raw
             if isinstance(v, (str, int)) and str(v).strip()]
    if len(parts) < 2:            # a lone city is not an address
        return None
    # "123 Main St, Frisco, TX 75033" — region and postcode belong together.
    head = ", ".join(parts[:-1]) if len(parts) > 2 else parts[0]
    return f"{head} {parts[-1]}" if len(parts) > 2 else ", ".join(parts)


def _ld_hours(node: dict) -> list[str]:
    """openingHours as a list of strings, whichever of the two shapes is used."""
    raw = node.get("openingHours") or node.get("openingHoursSpecification")
    out: list[str] = []
    for entry in (raw if isinstance(raw, list) else [raw] if raw else []):
        if isinstance(entry, str) and _DAY_RE.match(entry.strip()):
            out.append(_text(entry))
        elif isinstance(entry, dict):
            days = entry.get("dayOfWeek")
            days = days if isinstance(days, list) else [days] if days else []
            names = [str(d).rsplit("/", 1)[-1][:3] for d in days if d]
            opens, closes = entry.get("opens"), entry.get("closes")
            if names and opens and closes:
                out.append(f"{'-'.join(names)} {opens}-{closes}")
    return out[:7]


def read_structured_data(html: str) -> tuple[str | None, str | None, list[str]]:
    """(phone, address, hours) as the business publishes them about itself.

    Prefers schema.org, which is what a business tells search engines it is,
    and falls back to a tel: link — the number a visitor would actually tap.
    """
    phone = address = None
    hours: list[str] = []
    for node in _ld_nodes(html):
        types = node.get("@type")
        types = types if isinstance(types, list) else [types]
        if not any(isinstance(t, str) and (
                "Business" in t or "Store" in t or "Restaurant" in t
                or "Organization" in t or "Service" in t) for t in types):
            continue
        phone = phone or (_text(str(node.get("telephone"))) if node.get("telephone") else None)
        address = address or _ld_address(node)
        hours = hours or _ld_hours(node)
    if phone is None:
        found = _TEL_HREF_RE.search(html) or _PHONE_SHAPE_RE.search(html)
        if found:
            phone = _text(found.group(1))
    if phone and not _PHONE_SHAPE_RE.search(phone):
        phone = None              # an extension or a short code, not a number
    return phone, address, hours


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
    if _MARKETING_RE.search(text):        # headlines are copy, not offerings
        return None
    if _CHROME_RE.search(text):           # navigation, not an offering
        return None
    if _SECTION_RE.search(text):          # a page section heading, not an offering
        return None
    if text.endswith(","):                # half of a headline split over two lines
        return None
    if _CTA_RE.match(text):               # "Talk to a lawn expert" is a button
        return None
    if _ADDRESSES_READER_RE.search(text):  # "Areas We Serve" is copy, not a service
        return None
    if _MERCH_RE.search(text):            # a t-shirt is not a service
        return None
    if _PLACE_RE.match(text):             # a branch address, not an offering
        return None
    if len(_SOCIAL_PILE_RE.findall(text)) >= 2:   # a footer row of social links
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
    out.site_host = urlparse(base_url).netloc.lower().replace("www.", "")
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
            (out.products if _PRODUCT_RE.search(name) else out.services).append(name)
    for fragment in _LI_RE.findall(clean):
        if len(out.services) >= 12:
            break
        name = _clean_service(fragment)
        if name and name.lower() not in seen and " " in name:
            seen.add(name.lower())
            (out.products if _PRODUCT_RE.search(name) else out.services).append(name)
    out.services = out.services[:12]
    out.products = out.products[:8]

    out.phone, out.address, ld_hours = read_structured_data(html)
    out.mobile_ready = bool(_VIEWPORT_RE.search(html))
    # _TAG_RE strips script and style bodies; _ANY_TAG_RE strips the markup.
    out.text_words = len(_ANY_TAG_RE.sub(" ", _TAG_RE.sub(" ", html)).split())
    out.js_rendered = out.text_words < 120 and bool(_SPA_RE.search(html))
    out.https = base_url.lower().startswith("https")

    # Match the href AND the link text: a multi-location brand often uses a
    # "LOCATIONS" dropdown with no /locations URL behind it, which is how a
    # three-city restaurant group went unflagged.
    out.has_locations_page = bool(
        re.search(r'href=["\'][^"\']*/(locations?|our-locations|find-us)\b',
                  clean, re.IGNORECASE)
        or re.search(r">\s*(our\s+)?locations\s*<", clean, re.IGNORECASE)
    )
    out.menu_items = extract_menu_items(clean)
    out.menu_media = extract_menu_media(clean, base_url)

    page_text = _text(clean)
    # Structured data first: it is what the business tells search engines, and
    # it survives a footer whose opening times are drawn as an image.
    out.hours = _dedupe_hours(
        ld_hours + [m.group(0).strip() for m in _HOURS_RE.finditer(page_text)])[:7]

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
    """Fold a secondary page (contact/about/menu) into the homepage's extraction."""
    primary.site_host = primary.site_host or extra.site_host
    primary.has_locations_page = primary.has_locations_page or extra.has_locations_page
    primary.about = primary.about or extra.about
    primary.phone = primary.phone or extra.phone
    primary.mobile_ready = primary.mobile_ready or extra.mobile_ready
    primary.address = primary.address or extra.address
    primary.description = primary.description or extra.description
    for svc in extra.services:
        if svc.lower() not in {s.lower() for s in primary.services} and len(primary.services) < 12:
            primary.services.append(svc)
    for product in extra.products:
        if (product.lower() not in {p.lower() for p in primary.products}
                and len(primary.products) < 8):
            primary.products.append(product)
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
    for media in extra.menu_media:
        if media["url"] not in {m["url"] for m in primary.menu_media}:
            primary.menu_media.append(media)
    known = {i["name"].lower() for i in primary.menu_items}
    for item in extra.menu_items:
        if item["name"].lower() not in known and len(primary.menu_items) < 24:
            known.add(item["name"].lower())
            primary.menu_items.append(item)
    return primary


_MEDIA_RE = re.compile(r"\.(pdf|png|jpe?g|webp)(\?|$)", re.IGNORECASE)
# Assets are not pages. A stylesheet called "menu-addon.css" was being fetched
# as if it were the menu, purely because the filename contains "menu".
_ASSET_RE = re.compile(r"\.(css|js|json|xml|svg|ico|woff2?|ttf|map)(\?|$)",
                       re.IGNORECASE)
_MENU_WORD_RE = re.compile(r"menu|drinks?|dinner|lunch|brunch|breakfast|price",
                           re.IGNORECASE)


def extract_menu_media(html: str, base_url: str) -> list[dict]:
    """Menu PDFs / photos they publish, to embed rather than link away to."""
    base_host = urlparse(base_url).netloc.lower()
    out: list[dict] = []
    for href, label_html in _LINK_RE.findall(html or ""):
        absolute = urljoin(base_url, href)
        if urlparse(absolute).netloc.lower() != base_host:
            continue
        media = _MEDIA_RE.search(absolute)
        if not media:
            continue
        label = _text(label_html)
        if not (_MENU_WORD_RE.search(absolute) or _MENU_WORD_RE.search(label)):
            continue
        if _JUNK_IMAGE_RE.search(absolute):
            continue
        kind = "pdf" if media.group(1).lower() == "pdf" else "image"
        if absolute not in {m["url"] for m in out}:
            out.append({"url": absolute, "kind": kind, "label": label[:60] or "Menu"})
        if len(out) >= 4:
            break
    return out


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
        if _ASSET_RE.search(absolute):
            continue
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



def menu_page_urls(html: str, base_url: str, limit: int = 3) -> list[str]:
    """Links to their menu / price-list pages, so the new site can carry them."""
    base_host = urlparse(base_url).netloc.lower()
    found: list[str] = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html or "", re.IGNORECASE):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc.lower() != base_host:
            continue
        if _MEDIA_RE.search(absolute):     # a PDF/photo menu is media, not a page
            continue
        if _ASSET_RE.search(absolute):     # stylesheets and scripts are not pages
            continue
        last = parsed.path.strip("/").lower().split("/")[-1]
        if any(last == m or last.startswith(m) for m in _MENU_PATHS):
            if absolute not in found:
                found.append(absolute)
        if len(found) >= limit:
            break
    return found
