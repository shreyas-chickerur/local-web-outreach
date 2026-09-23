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
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)
_HEADING_RE = re.compile(r"<h([1-3])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL)
# The whole <img> tag, so lazy-loading attributes and the caption can be read
# off it. Matching only src= missed every photo on a site that defers loading —
# which is most of them now, and included the one dish this restaurant is
# currently promoting.
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*["\']([^"\']*)["\']')
# In priority order: the real source first, then the common lazy attributes.
_SRC_ATTRS = ("src", "data-src", "data-lazy-src", "data-original", "data-lazy")


# WordPress writes resized copies as name-WIDTHxHEIGHT.ext and keeps the
# original beside them. The page links the small one; we want the big one.
_RESIZED_RE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.\w{3,4}(?:\?|$))")


def full_size(url: str) -> str:
    """The original upload behind a resized copy, when the name gives it away."""
    return _RESIZED_RE.sub("", url)


def _img_sources(html: str) -> list[tuple[str, str]]:
    """(url, caption) for every image, however the page defers loading it."""
    found: list[tuple[str, str]] = []
    for tag in _IMG_TAG_RE.findall(html):
        attrs = {k.lower(): v for k, v in _ATTR_RE.findall(tag)}
        url = next((attrs[a] for a in _SRC_ATTRS
                    if attrs.get(a) and not attrs[a].startswith("data:")), "")
        if not url and attrs.get("srcset"):
            url = attrs["srcset"].split(",")[0].strip().split(" ")[0]
        if url and not url.startswith("data:"):
            found.append((full_size(url),
                          _text(attrs.get("title") or attrs.get("alt") or "")))
    return found
_LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                      re.IGNORECASE | re.DOTALL)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)

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
# A price with no dollar sign, trusted only when it is the whole line: that is
# how a menu's price column prints once the table is flattened ("Salmon", then
# "18.95"). Fish Shack's eighty-dish menu read as one item without this. Inside
# prose a bare decimal is a rating or a time, so it never counts there.
_BARE_PRICE_LINE_RE = re.compile(r"^\d{1,3}\.\d{2}$")
# What can sit between a dish and its price column, all found on Fish Shack's
# menu: the dish's other price ("13.95" then "10.95"), a size or count label
# ("large", "(6)", "1/2 Pound"), and a line saying what it comes with. Each was
# printed as the dish's name before it was skipped here.
_BETWEEN_NAME_AND_PRICE_RE = re.compile(
    r"^(?:\d{1,3}\.\d{2}"
    r"|(?:large|small|regular|half|whole|cup|bowl)"
    r"(?:\s+(?:large|small|regular|half|whole|cup|bowl))*"
    r"|\(\d+\)"
    r"|(?:\d+/\d+|one|half a)\s+(?:pound|lb)s?"
    r"|(?:all\s+)?served with .*)$", re.IGNORECASE)
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
        if _BARE_PRICE_LINE_RE.match(line):
            price, description = f"${line}", ""
            k = i - 1
            while k > 0 and _BETWEEN_NAME_AND_PRICE_RE.match(lines[k]):
                k -= 1
            name = lines[k].strip(" .-–—|") if k >= 0 else ""
        else:
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

# The first path segment that means "this is a profile" — anything else on
# these hosts is a single post, a share widget or a search result. Linking a
# business's "Instagram" to one reel from 2022 is worse than not linking it.
_PROFILE_RULES: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    # host: (segments that are NEVER a profile, segments that always ARE one)
    "instagram.com": (frozenset({"p", "reel", "reels", "explore", "stories",
                                 "tv", "s", "accounts"}), frozenset()),
    "facebook.com": (frozenset({"sharer", "sharer.php", "plugins", "tr",
                                "dialog", "permalink.php", "photo.php",
                                "events", "posts", "share"}), frozenset()),
    "twitter.com": (frozenset({"intent", "share", "home", "search", "hashtag",
                               "i", "status"}), frozenset()),
    "x.com": (frozenset({"intent", "share", "home", "search", "hashtag", "i",
                         "status"}), frozenset()),
    "tiktok.com": (frozenset({"video", "tag", "music", "discover"}), frozenset()),
    "youtube.com": (frozenset({"watch", "shorts", "results", "playlist",
                               "embed"}),
                    frozenset({"channel", "c", "user"})),
    "linkedin.com": (frozenset({"feed", "posts", "sharing", "shareArticle"}),
                     frozenset({"company", "in", "school"})),
    "yelp.com": (frozenset({"search", "writeareview"}), frozenset({"biz"})),
}


def _social_profile(host: str, path: str) -> str | None:
    """The platform this URL is a profile on, or None.

    Two mistakes to avoid, both seen in the wild on one restaurant's footer:
    matching the host by suffix classified `prairiefarmsteadtx.com` as X
    (it ends with "x.com"), and accepting any path linked a business's
    Instagram to a single reel.
    """
    host = host.lower().removeprefix("www.")
    for domain, name in _SOCIAL_HOSTS.items():
        # Exact domain or a real subdomain of it — never a suffix match.
        if host != domain and not host.endswith("." + domain):
            continue
        segments = [part for part in path.split("/") if part]
        if not segments:
            return None                      # the platform's front page
        banned, required = _PROFILE_RULES.get(domain, (frozenset(), frozenset()))
        first = segments[0].lower()
        if first in banned:
            return None
        if required and first not in required and not first.startswith("@"):
            return None
        if domain == "tiktok.com" and not first.startswith("@"):
            return None
        # A profile is one segment deep; anything longer is a post inside it.
        if len(segments) > 2:
            return None
        return name
    return None

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
    r"facebook|instagram|arrow|chevron|btn|button|screenshot|screen-shot)",
    re.IGNORECASE)

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
    # Every image or icon that might be the business's logo, in page order:
    # {url, source, label}. Ranked once the business's name is known
    # (`app.workbench.brief._pick_logo`); `logo` holds the winner.
    logo_candidates: list[dict] = field(default_factory=list)
    logo: str | None = None
    # A dedicated locations page is the clearest sign of more than one branch.
    has_locations_page: bool = False
    # A business publishing its own phone and address is an independent source:
    # it is what lets a directory's claim reach two-source confirmation.
    phone: str | None = None
    address: str | None = None
    # What each self-published fact was read out of: {field: {quote, found_in}}.
    # Carried so the operator screen can show the sentence beside the value,
    # and so a correction is a judgement about evidence rather than about a
    # number that appeared from nowhere.
    evidence: dict[str, dict] = field(default_factory=dict)
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
    # How much the about text reads like a business talking about itself.
    about_score: float = 0.0
    # Headed blocks lifted whole from their page: {heading, text, images, kind}.
    # Chasing one missing section at a time (their philosophy, their awards,
    # their farm partners) was losing to a page that simply has more on it than
    # our fixed list of sections.
    blocks: list[dict] = field(default_factory=list)

    def is_empty(self) -> bool:
        # The logo counts: a site whose one usable thing was its logo lost it
        # here, because nothing else made `published` worth serializing.
        return not any((self.about, self.services, self.products, self.hours, self.actions,
                        self.images, self.menu_items, self.logo))


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
# Ten digits in a row are not a phone number, and this pattern used to say they
# were. Two things were missing.
#
# It had no boundaries, so it matched *inside* a longer token: WordPress writes
# an edited image as "logo_Black1-e1568175315.png", and the ten digits of that
# Unix timestamp were published as the number to call. `(?<![\w-])` and
# `(?![\w-])` mean a match has to start and end at a real edge, which is the
# whole fix for that class — order numbers, licence numbers, tracking numbers
# and timestamps all live inside a longer run of characters.
#
# And it accepted a bare, unpunctuated run of ten digits anywhere on a page.
# A number a business wants rung is written the way people read numbers, with
# brackets or separators; an unpunctuated run needs a word nearby saying what
# it is. `_PHONE_WRITTEN_RE` is the first, `_PHONE_WORD_RE` supplies the second.
_PHONE_SHAPE_RE = re.compile(
    r"(?<![\w-])(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})(?![\w-])")
# The same number as a person would write it: brackets, or a separator between
# the groups. "(469) 664-0100" and "469.664.0100" qualify; "4696640100" does not.
_PHONE_WRITTEN_RE = re.compile(r"\(\d{3}\)|\d{3}[-.\s]\d{3}[-.\s]\d{4}")
# What a page says next to a number it wants rung.
_PHONE_WORD_RE = re.compile(
    r"\b(call|calling|phone|telephone|tel|mobile|cell|text|dial|reach us|"
    r"speak to|ring|reservations?|book|contact)\b", re.IGNORECASE)
_DAY_RE = re.compile(r"^(mo|tu|we|th|fr|sa|su)", re.IGNORECASE)

# A street address as a person writes one: a house number, a street name, the
# word that says what kind of street it is, then the town and the state. The
# state is not optional — "500 Main Street" alone appears in prose about
# somewhere else far too often to be read as where this business is.
_STREET_SUFFIX = (
    r"(?:st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|ln|lane|way|"
    r"ct|court|cir|circle|pkwy|parkway|hwy|highway|ter|terrace|pl|place|"
    r"trl|trail|sq|square|loop|row|pike|expy|expressway)"
)
_ADDRESS_RE = re.compile(
    r"\b(?P<num>\d{1,6}[A-Za-z]?)\s+"                       # house number
    r"(?:[NSEW]\.?\s+|North\s+|South\s+|East\s+|West\s+)?"   # optional quarter
    # The street's name, in words. A bare number is not one of them: allowing
    # one let the tail of a phone number ("…0100  7110 Main St.") be read as
    # the house number, with the real house number inside the street name.
    r"(?:(?:[A-Z][\w'.-]*|\d{1,3}(?:st|nd|rd|th))\s+){0,4}"
    rf"(?i:{_STREET_SUFFIX})\.?"                            # what kind of street
    r"(?:\s*,?\s*(?i:ste|suite|unit|apt|bldg|#)\s*[\w-]+)?"  # optional unit
    # A footer writes "7110 Main St. Frisco, TX 75033" and an about page writes
    # "7110 Main Street in Frisco, TX" — neither puts a comma before the town,
    # and requiring one meant the only two places this business states its own
    # address both went unread.
    r"\s*,?\s*(?:in\s+)?"
    r"(?P<city>[A-Z][\w'.-]*(?:\s+[A-Z][\w'.-]*){0,2})"     # the town
    r"\s*,\s*(?P<state>[A-Z]{2})"                           # the state
    r"(?:\s+(?P<zip>\d{5}(?:-\d{4})?))?"                    # and a postcode
)
# What a page says around the address it means as its own.
_ADDRESS_WORD_RE = re.compile(
    r"\b(address|located|location|find us|visit us|come see us|directions|"
    r"stop by|see us at|we(?:'re| are) at|map)\b", re.IGNORECASE)


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


def read_structured_data(
        html: str) -> tuple[str | None, str | None, list[str], dict[str, dict]]:
    """(phone, address, hours, evidence) as the business publishes them.

    Prefers schema.org, which is what a business tells search engines it is,
    and falls back to a tel: link — the number a visitor would actually tap.

    The fourth return is what each of the three was read out of: the schema
    type and property, or the surrounding line of the page. A fact without its
    evidence can be scored but it cannot be checked, and checking is the whole
    job of the screen this feeds.
    """
    phone = address = None
    hours: list[str] = []
    evidence: dict[str, dict] = {}

    def note(name: str, quote: str, found_in: str) -> None:
        if name not in evidence and quote:
            evidence[name] = {"quote": _text(str(quote))[:300], "found_in": found_in}

    for node in _ld_nodes(html):
        types = node.get("@type")
        types = types if isinstance(types, list) else [types]
        if not any(isinstance(t, str) and (
                "Business" in t or "Store" in t or "Restaurant" in t
                or "Organization" in t or "Service" in t) for t in types):
            continue
        named = next((t for t in types if isinstance(t, str)), "Thing")
        where = f"schema.org {named}"
        if phone is None and node.get("telephone"):
            phone = _text(str(node["telephone"]))
            note("phone", node["telephone"], f"{where} \u00b7 telephone")
        if address is None:
            found_address = _ld_address(node)
            if found_address:
                address = found_address
                raw = node.get("address")
                note("address",
                     json.dumps(raw, ensure_ascii=False) if isinstance(raw, dict)
                     else str(raw or found_address),
                     f"{where} \u00b7 address")
        if not hours:
            found_hours = _ld_hours(node)
            if found_hours:
                hours = found_hours
                note("hours", "; ".join(found_hours),
                     f"{where} \u00b7 openingHours")

    if phone is None:
        found = _TEL_HREF_RE.search(html)
        if found:
            phone = _text(found.group(1))
            note("phone", _line_around(html, found.start()),
                 "a telephone link on the page")
    if phone is None:
        # Ten digits in a row are not a phone number. WordPress appends a Unix
        # timestamp to an edited image — "…logo_Black1-e1568175315.png" — and
        # that string sits in the page's own structured data, where the shape
        # check found it and published it as the number to call. So the
        # fallback reads only what a visitor can see: a number nobody can read
        # off the page is not a number anybody will ring.
        visible = _ANY_TAG_RE.sub(" ", _TAG_RE.sub(" ", html))
        for found in _PHONE_SHAPE_RE.finditer(visible):
            written = found.group(2)
            nearby = visible[max(0, found.start() - 90): found.end() + 40]
            # Punctuated the way a person writes a number, or introduced by a
            # word that says what it is. Neither, and it is an identifier that
            # happens to be ten digits long.
            if not (_PHONE_WRITTEN_RE.search(written)
                    or _PHONE_WORD_RE.search(nearby)):
                continue
            phone = _text(written)
            note("phone", _line_around(visible, found.start(), already_text=True),
                 "the page's own words")
            break
    if phone and not _PHONE_SHAPE_RE.search(phone):
        phone = None              # an extension or a short code, not a number
        evidence.pop("phone", None)

    if address is None:
        # Same reasoning as the phone: read only what a visitor can see, and
        # only where the page is plainly saying where it is. A site that
        # publishes no PostalAddress still writes its address in the footer,
        # and without this the address has one source forever — Google — and
        # can never reach the two-source agreement the screen is built on.
        visible = _ANY_TAG_RE.sub(" ", _TAG_RE.sub(" ", html))
        found_all = list(_ADDRESS_RE.finditer(visible))
        # One place written twice is still one place: the footer's "7110 Main
        # St. Frisco, TX 75033" and the about page's "7110 Main Street in
        # Frisco, TX" differ as text and agree on everything that matters.
        places = {(m.group("num"), m.group("city").lower(), m.group("state"))
                  for m in found_all}
        introduced = [m for m in found_all if _ADDRESS_WORD_RE.search(
            visible[max(0, m.start() - 120): m.end() + 40])]
        # Introduced as an address, or the only place on the page — either way
        # it is this business's. Several different ones, none of them
        # introduced, could be a list of somebody else's.
        pool = introduced or (found_all if len(places) == 1 else [])
        if pool:
            found = max(pool, key=lambda m: bool(m.group("zip")))
            address = _text(found.group(0))
            note("address", _line_around(visible, found.start(), already_text=True),
                 "the page's own words")
    return phone, address, hours, evidence


def _line_around(html: str, at: int, width: int = 140, *,
                 already_text: bool = False) -> str:
    """The readable sentence a match sits in, markup removed.

    Quoting the raw markup would technically be the source's own words and
    would be unreadable, which defeats the point: somebody has to recognise
    this on the page they are looking at. `already_text` is for a caller that
    searched the stripped text, where the offset means nothing in the markup.
    """
    start, end = max(0, at - width), at + width
    # Widened to the nearest space on each side: a fixed character count lands
    # inside words, and Fish Shack's footer was quoted as "asual Oyster Bar".
    # Capped, because minified markup can run for thousands of characters
    # without a space.
    floor, ceiling = max(0, start - 40), min(len(html), end + 40)
    while start > floor and not html[start - 1].isspace():
        start -= 1
    while end < ceiling and not html[end].isspace():
        end += 1
    window = html[start:end]
    if already_text:
        return _text(window)
    return _text(_ANY_TAG_RE.sub(" ", _TAG_RE.sub(" ", window)))


# Words a business uses when it talks about itself, and words it uses when it
# is trying to take a booking. A paragraph headed "Our story" has to be the
# first kind.
_STORY_WORDS = re.compile(
    r"\b(we|our|us|founded|started|began|opened|family|generations?|tradition|"
    r"passion|passionate|proud|chef|owner|born|roots|recipe|recipes|craft|"
    r"handmade|scratch|locally|community|neighbou?rhood|history|story|"
    r"believe|dedicated|committed|inspired|journey|est|since)\b",
    re.IGNORECASE)
_TRANSACTIONAL = re.compile(
    r"(click here|click link|inquire|enquire|rsvp|book now|order now|"
    r"call us|email us|fill out|form below|terms|privacy|cookie|"
    r"subscribe|newsletter|gift card|free estimate|get a quote|chat with|"
    r"schedule (your|a|an)|request (your|a|an)|sign up|learn more|"
    r"@|\$\d|\d{3}[-.]\d{3}[-.]\d{4})",
    re.IGNORECASE)
# Below this a paragraph is not a story, and a heading promising one is worse
# than no section at all.
STORY_BAR = 5.0


_LEAD_HEADING = re.compile(
    r"^(?:[A-Z][A-Z&' ]{3,40}?(?=[A-Z][a-z])"      # SHOUTED HEADING then a Sentence
    r"|[A-Z][\w' ]{2,40}\?\s+)")                   # "Why Choose Us?" then the text


def strip_leading_heading(text: str) -> str:
    """Drop a heading that ran into the paragraph.

    Extracting a block often catches the heading above it, so an about section
    would open with "UPCOMING EVENTS" or "Why Choose Us" before saying anything.
    """
    return _LEAD_HEADING.sub("", text.strip(), count=1).strip()


def story_score(text: str) -> float:
    """How much this reads like a business describing itself.

    Rewards the vocabulary of self-description, penalises the vocabulary of a
    booking form, and mildly favours longer passages — a real story is rarely
    one line.
    """
    if not text:
        return 0.0
    words = len(text.split())
    story = len(_STORY_WORDS.findall(text))
    selling = len(_TRANSACTIONAL.findall(text))
    # The floor stops a fifteen-word call-to-action scoring like an essay:
    # "Call us — chat with our team" is almost all story words by density.
    density = story / max(words, 45) * 100
    length_bonus = min(words / 120, 1.0)
    return max(0.0, density + length_bonus - selling * 3.0)


_HEADED_BLOCK_RE = re.compile(r"<h([234])[^>]*>(.*?)</h\1>(.*?)(?=<h[234]\b|\Z)",
                              re.IGNORECASE | re.DOTALL)

_BLOCK_KINDS: tuple[tuple[str, str], ...] = (
    (r"james beard|award|nominat|winner|voted|best of|michelin|recogni", "award"),
    (r"partner|supplier|purveyor|producers?|farms?|friends of|we work with|"
     r"sourcing|sourced from", "partners"),
    (r"philosoph|our story|history|heritage|who we are|about us", "story"),
    (r"event|private dining|venue|parties|catering", "events"),
    (r"press|featured in|as seen", "press"),
)

# A block has to say something. Nav lists and button rows have headings too.
# Raised from 12: Cause 4 of "thicken the brief" — the deeper, budget-wide
# crawl this round added (CRAWL_DEPTH=2, up to CRAWL_PAGE_BUDGET pages,
# `app.workbench.brief`) reads far more of a site's own pages than a single
# homepage fetch ever did, and every one of them is a new source of the
# exact nav-soup `reads_as_prose()` exists to reject (a footer's opening
# hours restated under a heading, a caption row). A slightly higher floor
# keeps that filter meaningful as the number of candidate blocks grows,
# without touching the OTHER two things that already decide "is this
# real": a sentence-ending mark must be present, and capitalised words
# must stay under 42% — a short block that clears those two still has to
# clear this one.
_BLOCK_MIN_WORDS = 15
# Opening times, and the label rows that sit beside them.
_TIME_RE = re.compile(r"\d{1,2}(:\d{2})?\s?(am|pm)\b", re.IGNORECASE)


def reads_as_prose(text: str) -> bool:
    """Is this sentences, or a row of labels that happens to sit under a heading?

    "Sunday – Wednesday: 5pm – 9pm Thursday – Saturday: 5pm – 10pm Reserve A
    Table Chef's Tasting Menu Reservation Location" cleared a word count and
    was published as a paragraph about dinner service.
    """
    words = text.split()
    if len(words) < _BLOCK_MIN_WORDS:
        return False
    if not re.search(r"[.!?]", text):          # no sentence ends anywhere
        return False
    times = len(_TIME_RE.findall(text))
    if times >= 2:                             # an opening-hours table
        return False
    # Nav labels are Title Case runs; prose is mostly lower case.
    capitalised = sum(1 for w in words if w[:1].isupper())
    return capitalised / len(words) < 0.42


def _block_kind(heading: str) -> str:
    for pattern, kind in _BLOCK_KINDS:
        if re.search(pattern, heading, re.IGNORECASE):
            return kind
    return "feature"


# Headings that are furniture on any site. Deliberately NOT _NAV_NOISE, which
# was built to reject service names and contains real block headings like
# "philosophy" and "about us" — using it here threw away the best content on
# the page.
_BLOCK_STOP = frozenset({
    "home", "menu", "menus", "search", "cart", "checkout", "login", "log in",
    "sign up", "newsletter", "subscribe", "follow us", "navigation",
    "main menu", "privacy", "terms", "sitemap", "site map",
})

# How much of a single block's own text to keep. Doubled from 900: a real
# "our story" or "philosophy" page — read live building this fix — runs to
# two full paragraphs, and 900 characters was cutting genuine substance
# partway through a sentence, not trimming padding.
_BLOCK_TEXT_LIMIT = 1800
# How many of a page's headed sections to keep — both HERE, at one page's
# own extraction, and again in `merge()` once several pages are combined.
# Raised again, from 20 to 40: a single uncapped measurement across real
# fixtures found natural block counts from 6 to 227 with the depth-2 crawl,
# and 20 was binding on the large majority of them. There is no single
# number that stops binding on all of them without also swallowing noise —
# inspecting law-rich's own blocks past position ~35 found individual FAQ
# sub-questions from deep practice-area subpages and an unrelated sponsored
# blog post (a Baylor Athletics feature), not further distinct sections
# about the business itself. 40 roughly doubles the previous cap, clears
# every fixture that was genuinely under the old one, and reaches well into
# the largest sites' real content (awards, admissions, client testimonials,
# in-the-news items) before crossing into that per-FAQ granularity. Fully
# unbinding the largest sites would mean deduplicating near-identical
# per-page content, a crawl-shape problem, not a cap problem.
_BLOCK_LIMIT = 40

# How many named services / products to keep — at one page's own
# extraction and again once pages are merged, same reasoning as
# `_BLOCK_LIMIT` above (a mismatched pair of caps means the smaller one
# always wins first, so both move together). A multi-page crawl now reads
# a menu, a drinks list, a services page, and a service-area page that a
# single homepage fetch never saw — a lawn-care company's or a bar's real
# offering list is often longer than a dozen items once the whole site is
# actually read, and a shop's product range is often more than eight.
_SERVICE_LIMIT = 20
_PRODUCT_LIMIT = 15


def read_blocks(html: str, base_url: str) -> list[dict]:
    """The page's own sections, lifted whole.

    Their site is organised into headed blocks — Philosophy, A Few of Our
    Partners, James Beard Awards — and rebuilding from a fixed list of sections
    threw all of that away. Three shapes have to be handled, because this is
    how pages are actually written:

    * a heading with prose under it — the ordinary case;
    * a heading with nothing under it followed by a second heading, which is a
      kicker and its line ("James Beard Awards 2024" / "Nominated for Best
      Chef – Texas");
    * a container heading followed by a run of short headings, each an entry —
      which is what a partners or suppliers list looks like in markup.
    """
    raw: list[dict] = []
    for _level, heading_html, body in _HEADED_BLOCK_RE.findall(html):
        heading = _text(heading_html)
        if not heading or len(heading) > 70:
            continue
        if _CHROME_RE.search(heading) or heading.lower() in _BLOCK_STOP:
            continue
        raw.append({
            "heading": heading,
            "text": _text(_ANY_TAG_RE.sub(" ", body))[:_BLOCK_TEXT_LIMIT],
            "images": [urljoin(base_url, url) for url, _ in _img_sources(body)
                       if not _JUNK_IMAGE_RE.search(url)][:8],
        })

    blocks: list[dict] = []
    index = 0
    while index < len(raw):
        current = dict(raw[index])
        kind = _block_kind(current["heading"])

        # A container heading followed by short ones: each is an entry. Checked
        # BEFORE the kicker merge, or "A Few of Our Partners" gets folded into
        # the first farm and the list loses both its name and its first item.
        entries: list[dict] = []
        if kind == "partners":
            look = index + 1
            while look < len(raw) and len(raw[look]["text"].split()) < _BLOCK_MIN_WORDS:
                entries.append({"name": raw[look]["heading"],
                                "note": raw[look]["text"].strip()[:90]})
                look += 1
            if entries:
                index = look - 1

        # A heading with nothing under it is a kicker for the one that follows.
        if not entries and not current["text"].strip() and index + 1 < len(raw):
            following = raw[index + 1]
            if len(following["text"].split()) < _BLOCK_MIN_WORDS * 2:
                current["kicker"] = current["heading"]
                current["heading"] = following["heading"]
                current["text"] = following["text"]
                current["images"] = current["images"] or following["images"]
                kind = _block_kind(f"{current['kicker']} {current['heading']}")
                index += 1

        current["kind"] = kind
        current["entries"] = entries
        index += 1

        # An award is short by nature — "Nominated for Best Chef, Texas" is the
        # whole thing — so the word minimum would drop the most persuasive
        # line on the page. It survived on one real site only because that
        # site happened to put pictures next to it.
        prose = reads_as_prose(current["text"])
        if not prose and kind not in ("award", "partners"):
            # Keep the heading and the pictures, drop the label soup: a block
            # is allowed to be a heading with an image, but not a heading with
            # a nav row pretending to be a paragraph.
            current["text"] = ""
        enough = (prose or entries
                  or (kind == "award" and (current.get("kicker") or current["text"])))
        if enough and not any(b["heading"].lower() == current["heading"].lower()
                              for b in blocks):
            blocks.append(current)
    return blocks[:_BLOCK_LIMIT]


def social_handle(url: str) -> str:
    """The account name out of a profile URL, letters and digits only."""
    path = urlparse(url).path.strip("/")
    segments = [p for p in path.split("/") if p]
    if not segments:
        return ""
    handle = segments[-1] if segments[0] in {"company", "in", "biz", "channel",
                                             "c", "user", "school"} else segments[0]
    return re.sub(r"[^a-z0-9]", "", handle.lstrip("@").lower())


def social_belongs_to(url: str, business: str) -> bool:
    """Is this profile the business's own?

    A restaurant that credits fourteen farms links fourteen other businesses'
    Instagram accounts. Every one of them is a valid profile URL on the right
    host — and linking a customer to their beef supplier's page instead of
    theirs is worse than showing no social links at all.
    """
    handle = social_handle(url)
    if not handle:
        return False
    name = re.sub(r"[^a-z0-9]", "", (business or "").lower())
    if not name:
        return False
    if handle in name or name in handle:
        return True
    # Allow a leading "the" and a trailing state or "tx"-style suffix either way.
    trimmed = re.sub(r"^the", "", name)
    handle_trimmed = re.sub(r"^the", "", handle)
    if trimmed and (handle_trimmed.startswith(trimmed)
                    or trimmed.startswith(handle_trimmed)):
        return True
    # Otherwise require most of the business's words to appear in the handle.
    words = [w for w in re.findall(r"[a-z]+", (business or "").lower())
             if len(w) > 2 and w not in {"the", "and"}]
    if not words:
        return False
    hits = sum(1 for w in words if w in handle)
    return hits >= max(2, len(words) - 1)


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

    # Not the longest paragraph: that rule picked a private-events booking
    # pitch off a restaurant's homepage and a page headed "Our story" ended up
    # telling nobody anything about them.
    paragraphs = [_text(p) for p in _P_RE.findall(clean)]
    best, best_score = None, 0.0
    for raw in (p for p in paragraphs if 80 <= len(p) <= 900):
        candidate = strip_leading_heading(raw)
        score = story_score(candidate)
        if score > best_score:
            best, best_score = candidate, score
    out.about = best if best_score >= STORY_BAR else None
    out.about_score = round(best_score, 2)

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
        if len(out.services) >= _SERVICE_LIMIT:
            break
        name = _clean_service(fragment)
        if name and name.lower() not in seen and " " in name:
            seen.add(name.lower())
            (out.products if _PRODUCT_RE.search(name) else out.services).append(name)
    out.services = out.services[:_SERVICE_LIMIT]
    out.products = out.products[:_PRODUCT_LIMIT]

    out.blocks = read_blocks(clean, base_url)
    out.phone, out.address, ld_hours, out.evidence = read_structured_data(html)
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
    out.logo_candidates = extract_logo_candidates(html, base_url)

    page_text = _text(clean)
    # Structured data first: it is what the business tells search engines, and
    # it survives a footer whose opening times are drawn as an image.
    written_hours = [m.group(0).strip() for m in _HOURS_RE.finditer(page_text)]
    out.hours = _dedupe_hours(ld_hours + written_hours)[:7]
    # read_structured_data only sees schema.org, so hours found in the page's
    # own text arrived with nothing to check them against. Record them here,
    # where they are read, in the same shape.
    if written_hours and "hours" not in out.evidence:
        out.evidence["hours"] = {
            "quote": _text(" · ".join(written_hours[:7]))[:300],
            "found_in": "the page's own words",
        }

    base_host = urlparse(base_url).netloc.lower().replace("www.", "")
    action_seen: set[str] = set()
    for href, label_html in _LINK_RE.findall(clean):
        label = _text(label_html)
        if not label or href.startswith(("#", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        link = urlparse(absolute)
        host = link.netloc.lower().replace("www.", "")

        platform = _social_profile(host, link.path)
        if platform:
            if platform not in {s["name"] for s in out.socials}:
                out.socials.append({"name": platform, "url": absolute})
        else:
            lowered = label.lower()
            for needles, kind in _ACTION_PATTERNS:
                if any(n in lowered for n in needles) and kind not in action_seen:
                    if not _action_allowed(absolute, base_host):
                        break
                    action_seen.add(kind)
                    out.actions.append({"label": label[:40], "url": absolute, "kind": kind})
                    break

    for src, _caption in _img_sources(clean):
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
    known = {c["url"] for c in primary.logo_candidates}
    primary.logo_candidates += [c for c in extra.logo_candidates if c["url"] not in known]
    primary.site_host = primary.site_host or extra.site_host
    primary.has_locations_page = primary.has_locations_page or extra.has_locations_page
    # An /about page beats the homepage when its text reads more like a story.
    if extra.about and extra.about_score > primary.about_score:
        primary.about, primary.about_score = extra.about, extra.about_score
    primary.about = primary.about or extra.about
    primary.phone = primary.phone or extra.phone
    primary.mobile_ready = primary.mobile_ready or extra.mobile_ready
    known = {b["heading"].lower() for b in primary.blocks}
    for block in extra.blocks:
        if block["heading"].lower() not in known and len(primary.blocks) < _BLOCK_LIMIT:
            primary.blocks.append(block)
    primary.address = primary.address or extra.address
    for name, found in extra.evidence.items():
        primary.evidence.setdefault(name, found)
    primary.description = primary.description or extra.description
    for svc in extra.services:
        if (svc.lower() not in {s.lower() for s in primary.services}
                and len(primary.services) < _SERVICE_LIMIT):
            primary.services.append(svc)
    for product in extra.products:
        if (product.lower() not in {p.lower() for p in primary.products}
                and len(primary.products) < _PRODUCT_LIMIT):
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
# "wine", "cocktail" and "beer" were missing, so The Heritage Table's wine
# list, published as an image, was never recognised as a menu at all.
_MENU_WORD_RE = re.compile(r"menu|drinks?|dinner|lunch|brunch|breakfast|price|wine|"
                           r"cocktails?|beers?",
                           re.IGNORECASE)


_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def _attr_value(tag: str, name: str) -> str:
    found = re.search(rf'\s{name}=["\']([^"\']*)["\']', tag, re.IGNORECASE)
    return found.group(1).strip() if found else ""


# Never a logo, whatever the file is called: The Heritage Table's sharing image
# is a James Beard seal, and Fish Shack's page carries a farm-raised badge.
_NOT_A_LOGO_RE = re.compile(r"seal|badge|award|medal|certif|winner|nominee",
                            re.IGNORECASE)


def extract_logo_candidates(html: str, base_url: str) -> list[dict]:
    """Everything on a page that might be the business's logo, in page order.

    Logos were filtered out with the other non-photographs, so no generated
    page ever carried the business's own mark. Three kinds are kept, ranked
    later against the business's name: a logo the page's structured data
    names, an image whose address, class or text says "logo", and a site icon
    large enough to stand in (a touch icon, or one declared 180 pixels or more).
    """
    out: list[dict] = []

    def add(url: str, source: str, label: str = "") -> None:
        url = urljoin(base_url, url.strip())
        if url.startswith("data:") or _NOT_A_LOGO_RE.search(url + " " + label):
            return
        if url not in {c["url"] for c in out}:
            out.append({"url": url, "source": source, "label": label})

    for found in re.finditer(r'"logo"\s*:\s*(?:"([^"]+)"|\{[^}]*?"url"\s*:\s*"([^"]+)")',
                             html or ""):
        add(found.group(1) or found.group(2), "structured data")
    for tag in _IMG_TAG_RE.findall(html or ""):
        src = _attr_value(tag, "data-src") or _attr_value(tag, "src")
        label = " ".join(_attr_value(tag, a) for a in ("alt", "title", "class"))
        if src and re.search(r"logo", f"{src} {label}", re.IGNORECASE):
            add(src, "logo image", label.strip())
    for tag in re.findall(r"<link\b[^>]*>", html or "", re.IGNORECASE):
        rel = _attr_value(tag, "rel").lower()
        sizes = re.findall(r"(\d+)x\d+", _attr_value(tag, "sizes"))
        big = "apple-touch-icon" in rel or (sizes and int(sizes[0]) >= 180)
        if "icon" in rel and big and _attr_value(tag, "href"):
            add(_attr_value(tag, "href"), "site icon")
    return out


def extract_menu_media(html: str, base_url: str) -> list[dict]:
    """Menu PDFs / photos they publish, to embed rather than link away to."""
    base_host = urlparse(base_url).netloc.lower()
    out: list[dict] = []
    # A menu can be a link to a file, or an image on the page itself. The
    # image's address may sit in data-src until it scrolls into view, with a
    # placeholder in src, and its only label in alt or title.
    candidates = list(_LINK_RE.findall(html or ""))
    for tag in _IMG_TAG_RE.findall(html or ""):
        src = _attr_value(tag, "data-src") or _attr_value(tag, "src")
        if src and not src.startswith("data:"):
            candidates.append((src, f"{_attr_value(tag, 'title')} {_attr_value(tag, 'alt')}"))
    for href, label_html in candidates:
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

# Everything else a small business puts on its own pages. The crawl used to
# fetch the homepage, the menu and the contact page, so a restaurant's story,
# its private-dining pitch, its press and its gallery were simply lost — and
# the generated site then had nothing to say in its About section because
# nobody had read the page where they said it.
_STORY_PATHS = (
    "our-story", "story", "history", "heritage", "philosophy", "mission",
    "team", "our-team", "chef", "chefs", "staff", "people", "who-we-are",
    "gallery", "photos", "pictures",
    "events", "private-events", "private-dining", "parties", "catering",
    "press", "awards", "accolades", "recognition", "reviews", "testimonials",
    "specials", "wine", "wine-list", "bar", "drinks",
    "experience", "dining", "visit", "faq", "sourcing", "partners", "farms",
)


def html_to_text(html: str) -> str:
    """Crude but dependency-free text extraction — enough to find contact info."""
    without_code = _TAG_RE.sub(" ", html or "")
    return re.sub(r"\s+", " ", _ANY_TAG_RE.sub(" ", without_code)).strip()


# Same-host paths that are real pages on the site but never worth reading:
# cart/checkout machinery, admin/login screens, syndication feeds, and the
# auto-generated archive pages (tag, category, author, pagination) a CMS
# produces by the hundred. None of it is the business talking about
# itself, and visiting it first would spend the whole page budget before
# a real page is ever reached.
_JUNK_PAGE_RE = re.compile(
    r"/(cart|checkout|account|my-account|login|wp-admin|wp-login|wp-json|"
    r"feed|rss|tag|category|author|page/\d+|search|sitemap)(/|$|[.?]|php)"
    r"|[?&]s="
    # WordPress short links repeat a page already reached by its real address,
    # and xmlrpc.php is an interface, not a page: together they took nine of
    # The Heritage Table's eighteen crawl slots.
    r"|[?&]p=\d+|xmlrpc\.php",
    re.IGNORECASE)

# The keyword lists are a PRIORITY ORDERING now, not a gate — see
# `content_page_urls`. Menu first (the highest-value page a restaurant's
# site can have), then contact, then everything else worth naming.
_PRIORITY_PATHS = _MENU_PATHS + _CONTACT_PATHS + _STORY_PATHS


def _priority(url: str) -> int:
    """Lower sorts first. A page whose last path segment names something
    on the priority list is worth reaching before the budget runs out;
    everything else is still a real candidate, just not moved to the
    front of the queue."""
    last = urlparse(url).path.strip("/").lower().split("/")[-1]
    for index, path in enumerate(_PRIORITY_PATHS):
        if last == path or last.startswith(path):
            return index
    return len(_PRIORITY_PATHS)


def content_page_urls(html: str, base_url: str, limit: int = 20) -> list[str]:
    """Same-host pages worth reading, priority-ordered.

    Used to be a keyword GATE, one level deep: only a link whose last path
    segment named "menu", "contact", "our-story" or similar was ever
    visited, and only from the homepage — a business whose personality
    lives on a page named something the lists never anticipated
    ("blackland-prairie-cuisine", a chef's-tasting-menu page) was invisible,
    and anything linked only from a SECOND page was never reached at all.

    Every same-host page (excluding assets, media, and known junk) is now a
    real candidate; the keyword lists just decide which ones are worth
    reaching FIRST when the page budget cannot fit them all.
    `app.workbench.brief._read_their_site` calls this at TWO levels (the
    homepage, then each page it fetched from that first level) for an
    actual depth-2 crawl — this function only ever looks at the ONE page's
    own links, exactly as before; the depth comes from calling it twice.
    """
    base_host = urlparse(base_url).netloc.lower()
    home = base_url.rstrip("/")
    found: list[str] = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html or "", re.IGNORECASE):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        absolute = urljoin(base_url, href).split("#", 1)[0]
        parsed = urlparse(absolute)
        if parsed.netloc.lower() != base_host:
            continue
        if _MEDIA_RE.search(absolute) or _ASSET_RE.search(absolute):
            continue
        if _JUNK_PAGE_RE.search(f"{parsed.path}?{parsed.query}".lower()):
            continue
        if absolute.rstrip("/") == home:
            continue
        if absolute not in found:
            found.append(absolute)
    found.sort(key=_priority)
    return found[:limit]


