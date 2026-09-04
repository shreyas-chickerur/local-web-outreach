"""Build a site out of what we actually know about a business.

The governing rule is the requirements' own: **no unverified fact ships**. The
page is shown to the owner, so one sentence they know to be false ends the
meeting — a fabricated "serving the neighbourhood since 1994" is worse than a
plain page. That is enforced structurally rather than by care:

* every value comes from `material_from_brief()` — their own published site, a
  fact two independent sources agreed on, something you confirmed yourself, or
  a Google review quoted with its author's name;
* generic copy is allowed ("Come and see us"); specific claims are not;
* a section with no data is absent, not filled with a placeholder that reads as
  a claim;
* `unsupported()` re-checks the finished page and the tests run it, so a future
  section cannot quietly start inventing.

Everything else here is craft: the page has to be worth showing, not merely
true.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from app.site.spec import SiteSpec, parse_spec
from app.site.styles import css, script
from app.site.theme import Theme, theme_for
from app.workbench.hours import parse_week

# Sections in the order they read, when nothing asks otherwise.
ORDER = ("hero", "stats", "services", "menu", "gallery", "reviews", "about",
         "hours", "contact")

_CTA_LABEL = {"call": "Call us", "book": "Book a table", "order": "Order online",
              "quote": "Get a quote", "visit": "Find us"}


@dataclass
class Material:
    """Everything the page is allowed to say, gathered in one place."""

    name: str
    tagline: str | None = None
    about: str | None = None
    services: tuple[str, ...] = ()
    products: tuple[str, ...] = ()
    menu_items: tuple[dict, ...] = ()
    hours: tuple[str, ...] = ()
    photos: tuple[str, ...] = ()
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    socials: tuple[dict, ...] = ()
    rating: float | None = None
    reviews: int | None = None
    trade: str | None = None
    quotes: tuple[dict, ...] = ()
    place_photos: tuple[str, ...] = ()
    lead_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_level: str | None = None

    @property
    def images(self) -> tuple[str, ...]:
        """Google's photography first: it is shot for the listing and is nearly
        always better than what the business put on its own site. Served
        through us, so the API key never appears in a page we hand over."""
        proxied: tuple[str, ...] = ()
        if self.lead_id is not None and self.place_photos:
            proxied = tuple(f"/photo/{self.lead_id}/{i}"
                            for i in range(len(self.place_photos)))
        return proxied + self.photos


def material_from_brief(brief: dict) -> Material:
    """Pull the usable content out of a brief.

    Facts are taken only when corroborated or confirmed by you: a phone number
    one directory guessed is exactly the sort that is wrong, and a wrong number
    on a demo site is the end of the meeting.
    """
    published = brief.get("published") or {}
    trusted = {f["field"]: f["value"] for f in brief.get("facts", [])
               if f.get("confidence") in ("verified", "operator_verified")
               and f.get("value")}
    ratings = brief.get("ratings") or []
    best = max(ratings, key=lambda r: (r.get("reviews") or 0), default=None)
    return Material(
        name=brief.get("name") or "",
        tagline=published.get("tagline"),
        about=published.get("about"),
        services=tuple(published.get("services") or ()),
        products=tuple(published.get("products") or ()),
        menu_items=tuple(published.get("menu_items") or ()),
        hours=tuple(published.get("hours") or ()) or (
            (trusted["hours"],) if "hours" in trusted else ()),
        photos=tuple(published.get("photos") or ()),
        address=trusted.get("address"),
        phone=trusted.get("phone"),
        email=(published.get("emails") or [None])[0],
        socials=tuple(published.get("socials") or ()),
        rating=best.get("value") if best else None,
        reviews=best.get("reviews") if best else None,
        trade=brief.get("trade"),
        price_level=brief.get("price_level"),
        quotes=tuple(brief.get("testimonials") or ()),
        place_photos=tuple(brief.get("place_photos") or ()),
        lead_id=brief.get("lead_id"),
        latitude=brief.get("latitude"),
        longitude=brief.get("longitude"),
    )


def e(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _digits(phone: str | None) -> str:
    return re.sub(r"[^\d+]", "", phone or "")


def _maps(query: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&amp;query={quote_plus(query)}"


# --------------------------------------------------------------------------- #
# Sections. Each returns "" when there is nothing real to put in it.
# --------------------------------------------------------------------------- #

_LABELS = {"services": "What we do", "menu": "Menu", "gallery": "Gallery",
           "reviews": "Reviews", "about": "About", "hours": "Hours",
           "contact": "Visit"}


def _nav(m: Material, present: list[str], spec: SiteSpec) -> str:
    """A one-page site without navigation is a scroll, not a site."""
    links = "".join(f'<a href="#{k}">{e(_LABELS[k])}</a>'
                    for k in present if k in _LABELS)
    book = ""
    if m.phone:
        book = (f'<a class="book" href="tel:{e(_digits(m.phone))}">'
                f'{e(_CTA_LABEL.get(spec.cta or "call", "Call us"))}</a>')
    return (f'<div class="progress"></div>\n<div class="bar">'
            f'<a class="mark" href="#top">{e(m.name)}</a>'
            f'<button class="burger" aria-label="Menu">&#9776;</button>'
            f'<nav>{links}</nav>{book}</div>')


def _cta(m: Material, spec: SiteSpec) -> str:
    """Only offer an action we can actually wire up."""
    if m.phone:
        label = _CTA_LABEL.get(spec.cta or "call", "Call us")
        if spec.cta in (None, "call"):
            label = f"Call {m.phone}"
        return f'<a class="cta" href="tel:{e(_digits(m.phone))}">{e(label)}</a>'
    if m.address:
        return (f'<a class="cta" href="{_maps(m.name + " " + m.address)}"'
                f' target="_blank" rel="noopener">Find us</a>')
    return ""


def _secondary(m: Material) -> str:
    if not m.address:
        return ""
    return (f'<a class="cta ghost" href="{_maps(m.name + " " + m.address)}"'
            f' target="_blank" rel="noopener">Get directions</a>')


def _hero(m: Material, spec: SiteSpec, t: Theme) -> str:
    photo = m.images[0] if m.images else None
    sub = m.tagline or m.about or m.trade or ""
    facts = []
    if m.rating and m.reviews:
        facts.append(f"<span>&#9733; {e(m.rating)} &middot; {e(m.reviews)} "
                     f"Google reviews</span>")
    if m.address:
        facts.append(f"<span>{e(m.address.split(',')[0])}</span>")
    if m.hours:
        facts.append(f"<span>{e(m.hours[0])}</span>")
    layers = ""
    if photo:
        layers = (f'<div class="bgimg" style="background-image:url(&quot;{e(photo)}&quot;)">'
                  f'</div><div class="veil"></div>')
    return (f'<header class="hero{" has-photo" if photo else ""}" id="top">{layers}'
            f'<div class="wrap"><h1>{e(m.name)}</h1>'
            + (f'<p class="sub">{e(sub)}</p>' if sub else "")
            + (f'<div class="facts">{"".join(facts)}</div>' if facts else "")
            + f'<div class="actions">{_cta(m, spec)}{_secondary(m)}</div></div>'
            + ('<div class="scrollcue"></div>' if photo else "")
            + "</header>")


_FOOD_TRADES = ("restaurant", "cafe", "coffee", "bakery", "bar", "pizza",
                "barbecue", "grill", "diner", "kitchen", "food")


def _offer_heading(m: Material) -> tuple[str, str]:
    """Name the section after what the business actually does."""
    trade = (m.trade or "").lower()
    if m.menu_items or any(word in trade for word in _FOOD_TRADES):
        return "On offer", "What we cook and serve"
    if m.products and not m.services:
        return "The shop", "What we make"
    return "What we do", "How we can help"


def _services(m: Material, t: Theme) -> str:
    """Photo-led where there are photos to lead with.

    A grid of bare titles is the tell of a generated page: the words are true
    and the section is empty. Their own photography carries it instead, and
    where there is none the type does the work rather than a numbered box.
    """
    items = list(m.services) + list(m.products)
    if not items:
        return ""
    eyebrow, heading = _offer_heading(m)
    # Keep the first image for the hero and the rest for the gallery; the
    # middle ones dress this section without starving either.
    art = m.images[1:1 + len(items)] if len(m.images) > 3 else ()
    cards = []
    for i, item in enumerate(items[:8]):
        photo = art[i] if i < len(art) else None
        if photo:
            cards.append(
                f'<article class="offer has-art" data-reveal data-delay="{i % 4}">'
                f'<div class="art"><img src="{e(photo)}" alt="" loading="lazy"'
                f' decoding="async"></div>'
                f'<div class="label"><span class="idx">{i + 1:02d}</span>'
                f'<h3>{e(item)}</h3></div></article>')
        else:
            cards.append(
                f'<article class="offer" data-reveal data-delay="{i % 4}">'
                f'<span class="idx">{i + 1:02d}</span><h3>{e(item)}</h3>'
                f'<span class="rule"></span></article>')
    lede = f'<p class="lede">{e(m.tagline)}</p>' if m.tagline else ""
    return (f'<section id="services"><div class="wrap">'
            f'<div class="head" data-reveal><p class="eyebrow">{e(eyebrow)}</p>'
            f'<h2>{e(heading)}</h2>{lede}</div>'
            f'<div class="offers">{"".join(cards)}</div></div></section>')


def _stats(m: Material, t: Theme) -> str:
    """A band of the few numbers we can stand behind.

    Counting things we actually have — reviews, dishes, the rating — rather
    than the invented "500+ happy customers" that makes a page worthless.
    """
    tiles = []
    if m.rating:
        tiles.append((f"{m.rating}", "average rating", ""))
    if m.reviews:
        tiles.append((f"{m.reviews}", "Google reviews", "count"))
    # Only count something we actually have: a proud "0 services offered" is
    # the kind of detail that loses the room.
    offerings = len(m.services) + len(m.products)
    if m.menu_items:
        tiles.append((f"{len(m.menu_items)}", "dishes on the menu", "count"))
    elif offerings:
        tiles.append((f"{offerings}", "services offered", "count"))
    if len(tiles) < 2:
        return ""
    cells = "".join(
        f'<div class="stat" data-reveal data-delay="{i}">'
        f'<b{(" data-count=" + chr(34) + value + chr(34)) if kind else ""}>'
        f'{e(value)}</b>'
        f'<span>{e(label)}</span></div>'
        for i, (value, label, kind) in enumerate(tiles))
    return (f'<section id="stats" class="statband"><div class="wrap">'
            f'<div class="stats">{cells}</div></div></section>')


def _menu(m: Material, t: Theme) -> str:
    if not m.menu_items:
        return ""
    groups: list[str] = []
    for item in m.menu_items:
        group = str(item.get("group") or "").strip()
        if group and group not in groups:
            groups.append(group)
    filters = ""
    if len(groups) > 1:
        buttons = ['<button data-group="all" aria-pressed="true">Everything</button>']
        buttons += [f'<button data-group="{e(g)}" aria-pressed="false">{e(g)}</button>'
                    for g in groups]
        filters = f'<div class="filters" data-reveal>{"".join(buttons)}</div>'
    rows = []
    for i, item in enumerate(m.menu_items[:24]):
        parts = [f'<span class="n">{e(item.get("name"))}</span>']
        if item.get("price"):
            parts.append(f'<span class="p">{e(item["price"])}</span>')
        if item.get("description"):
            parts.append(f'<p class="d">{e(item["description"])}</p>')
        rows.append(f'<li data-group="{e(item.get("group") or "All")}" data-reveal '
                    f'data-delay="{i % 4}">{"".join(parts)}</li>')
    return (f'<section id="menu" class="band"><div class="wrap">'
            f'<p class="eyebrow" data-reveal>On the menu</p>'
            f'<h2 data-reveal>What we serve</h2>{filters}'
            f'<ul class="dishes">{"".join(rows)}</ul></div></section>')


def _gallery(m: Material, t: Theme) -> str:
    shots = m.images[1:13]
    if len(shots) < 3:
        return ""
    tiles = "".join(
        f'<button aria-label="Open photo {i + 1}" data-reveal data-delay="{i % 4}">'
        f'<img src="{e(src)}" alt="" loading="lazy" decoding="async"></button>'
        for i, src in enumerate(shots))
    return (f'<section id="gallery"><div class="wrap">'
            f'<p class="eyebrow" data-reveal>Gallery</p>'
            f'<h2 data-reveal>Have a look around</h2>'
            f'<div class="mosaic">{tiles}</div></div></section>'
            f'<div class="lightbox" role="dialog" aria-label="Photo">'
            f'<button class="close" aria-label="Close">&times;</button>'
            f'<button class="prev" aria-label="Previous">&lsaquo;</button>'
            f'<img src="" alt="">'
            f'<button class="next" aria-label="Next">&rsaquo;</button>'
            f'<div class="count"></div></div>')


def _reviews(m: Material, t: Theme) -> str:
    """Their customers' words, attributed. The most credible copy on any small
    business site is the part the business did not write."""
    if len(m.quotes) < 2:
        return ""
    cards = []
    for i, quote in enumerate(m.quotes[:6]):
        stars = "&#9733;" * max(1, min(5, int(quote.get("rating") or 5)))
        text = str(quote.get("text") or "")[:340].strip()
        cards.append(f'<figure class="quote" data-reveal data-delay="{i % 4}">'
                     f'<div class="stars">{stars}</div>'
                     f'<p>&ldquo;{e(text)}&rdquo;</p>'
                     f'<figcaption class="who">{e(quote.get("author"))} '
                     f'&middot; Google</figcaption></figure>')
    headline = (f"{m.rating} stars from {m.reviews} reviews"
                if m.rating and m.reviews else "What people say")
    return (f'<section id="reviews" class="band"><div class="wrap">'
            f'<p class="eyebrow" data-reveal>Reviews</p>'
            f'<h2 data-reveal>{e(headline)}</h2>'
            f'<div class="quotes">{"".join(cards)}</div></div></section>')


# "Our story" promises a history. Text about how a place cooks is not one, and
# a heading that over-promises is the first thing an owner notices.
_HISTORY = re.compile(
    r"\b(founded|started|opened|began|since \d{4}|generations?|family|"
    r"grew up|years ago|est\.? ?\d{4}|history|heritage|tradition)\b",
    re.IGNORECASE)


def _about(m: Material, t: Theme) -> str:
    if not m.about:
        return ""
    heading = "Our story" if _HISTORY.search(m.about) else "What we are about"
    return (f'<section id="about"><div class="wrap"><div class="split">'
            f'<div data-reveal><p class="eyebrow">About</p><h2>{heading}</h2></div>'
            f'<div data-reveal data-delay="1">'
            f'<p style="font-size:clamp(17px,1.7vw,22px)">{e(m.about)}</p>'
            f'</div></div></div></section>')


def _hours(m: Material, t: Theme) -> str:
    if not m.hours:
        return ""
    week = json.dumps(parse_week(list(m.hours))).replace("'", "&#39;")
    rows = "".join(f"<li><span>{e(line)}</span></li>" for line in m.hours[:7])
    return (f'<section id="hours" class="band"><div class="wrap narrow">'
            f'<p class="eyebrow" data-reveal>Hours</p>'
            f"<div class=\"openflag\" data-week='{week}' data-reveal>"
            f'<i></i><span>Opening hours</span></div>'
            f'<ul class="hourlist" data-reveal data-delay="1">{rows}</ul>'
            f'</div></section>')


def _contact(m: Material, t: Theme) -> str:
    rows = []
    if m.address:
        rows.append(f'<a href="{_maps(m.address)}" target="_blank" rel="noopener">'
                    f'<span class="k">Address</span>'
                    f'<span class="v">{e(m.address)}</span></a>')
    if m.phone:
        rows.append(f'<a href="tel:{e(_digits(m.phone))}"><span class="k">Phone</span>'
                    f'<span class="v">{e(m.phone)}</span></a>')
    if m.email:
        rows.append(f'<a href="mailto:{e(m.email)}"><span class="k">Email</span>'
                    f'<span class="v">{e(m.email)}</span></a>')
    for social in m.socials[:4]:
        rows.append(f'<a href="{e(social.get("url"))}" target="_blank" rel="noopener">'
                    f'<span class="k">{e(social.get("name"))}</span>'
                    f'<span class="v">Follow along</span></a>')
    if not rows:
        return ""
    map_block = ""
    if m.latitude is not None and m.longitude is not None:
        lat, lon = m.latitude, m.longitude
        box = f"{lon - 0.004},{lat - 0.003},{lon + 0.004},{lat + 0.003}"
        # OpenStreetMap needs no key, so no credential is written into the page.
        map_block = (f'<div class="map" data-reveal data-delay="1">'
                     f'<iframe loading="lazy" title="Map of {e(m.name)}" '
                     f'src="https://www.openstreetmap.org/export/embed.html'
                     f'?bbox={box}&amp;layer=mapnik&amp;marker={lat},{lon}"></iframe></div>')
    return (f'<section id="contact"><div class="wrap"><div class="split">'
            f'<div data-reveal><p class="eyebrow">Visit</p><h2>Come and see us</h2>'
            f'<div class="reach">{"".join(rows)}</div></div>{map_block}'
            f'</div></div></section>')


def _callbar(m: Material, spec: SiteSpec) -> str:
    """On a phone the action should never be more than a thumb away."""
    if not m.phone:
        return ""
    label = _CTA_LABEL.get(spec.cta or "call", "Call us")
    directions = ""
    if m.address:
        directions = (f'<a class="cta ghost" href="{_maps(m.address)}"'
                      f' target="_blank" rel="noopener">Directions</a>')
    return (f'<div class="callbar"><a class="cta" href="tel:{e(_digits(m.phone))}">'
            f'{e(label)}</a>{directions}</div>')


def _schema(m: Material) -> str:
    """Structured data, so search and maps read the page correctly.

    The same facts already on the page, in the shape a crawler wants — not an
    extra set of claims.
    """
    data: dict = {"@context": "https://schema.org", "@type": "LocalBusiness",
                  "name": m.name}
    if m.address:
        data["address"] = {"@type": "PostalAddress", "streetAddress": m.address}
    if m.phone:
        data["telephone"] = m.phone
    if m.rating and m.reviews:
        data["aggregateRating"] = {"@type": "AggregateRating",
                                   "ratingValue": m.rating,
                                   "reviewCount": m.reviews}
    if m.latitude is not None:
        data["geo"] = {"@type": "GeoCoordinates", "latitude": m.latitude,
                       "longitude": m.longitude}
    return ('<script type="application/ld+json">'
            + json.dumps(data).replace("<", "\\u003c") + "</script>")


def _footer(m: Material) -> str:
    bits = [f"<span>&copy; {e(m.name)}</span>"]
    if m.address:
        bits.append(f"<span>{e(m.address)}</span>")
    if m.phone:
        bits.append(f'<a href="tel:{e(_digits(m.phone))}">{e(m.phone)}</a>')
    return (f'<footer><div class="wrap"><div class="row">{"".join(bits)}'
            f'<button class="top">Back to top</button></div></div></footer>')


_BUILDERS = {"stats": _stats, "services": _services, "menu": _menu, "gallery": _gallery,
             "reviews": _reviews, "about": _about, "hours": _hours,
             "contact": _contact}

_NO_DATA = {
    "menu": "they publish no prices we could read — often the menu is a PDF or "
            "a photo",
    "gallery": "there are not enough photos to build one",
    "services": "their site does not list what they offer in a readable way",
    "reviews": "no reviews with text came back for them",
    "stats": "there are not enough numbers we can stand behind",
    "hours": "no source publishes their opening hours",
    "about": "their site has no about text",
    "contact": "we have no address, phone or email to show",
}


def _order(spec: SiteSpec, available: set[str]) -> list[str]:
    order = [s for s in ORDER if s in available]
    for asked in ([spec.lead_with] if spec.lead_with else []) + spec.emphasis:
        if asked and asked not in available:
            spec.unmet.append(f"no {asked} section: {_NO_DATA.get(asked, 'no data')}")
    if spec.lead_with in order:
        order.remove(spec.lead_with)
        order.insert(1 if "hero" in order else 0, spec.lead_with)
    for section in reversed(spec.emphasis):
        if section in order and order.index(section) > 2:
            order.remove(section)
            order.insert(min(2, len(order)), section)
    return order


def build(brief: dict, spec_text: str = "") -> tuple[str, SiteSpec]:
    """Return (html, spec). Deterministic: same inputs, same page."""
    m = material_from_brief(brief)
    spec = parse_spec(spec_text)
    theme = theme_for(spec.mood)

    sections = {key: builder(m, theme) for key, builder in _BUILDERS.items()}
    available = {"hero"} | {k for k, v in sections.items() if v}
    order = _order(spec, available)

    body = _hero(m, spec, theme)
    for key in order:
        if key != "hero":
            body += "\n" + sections[key]

    description = m.tagline or m.about or ""
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{e(m.name)}</title>\n"
        + (f'<meta name="description" content="{e(description[:160])}">\n'
           if description else "")
        + f'<meta property="og:title" content="{e(m.name)}">\n'
        + (f'<meta property="og:image" content="{e(m.images[0])}">\n'
           if m.images else "")
        + '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        + '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        + f'<link href="{theme.fonts}" rel="stylesheet">\n'
        + f"<style>{css(theme)}</style>\n{_schema(m)}</head>\n<body>\n"
        + _nav(m, order, spec) + "\n" + body + "\n"
        + _callbar(m, spec) + "\n" + _footer(m)
        + f"\n<script>{script()}</script>\n</body></html>", spec)


# --------------------------------------------------------------------------- #
# The guard. Run by the tests against every generated page.
# --------------------------------------------------------------------------- #

_CLAIM_RE = re.compile(
    r"\b(since \d{4}|est\.? ?\d{4}|\d+\+? years|award[- ]winning|voted|"
    r"best in|number one|#1|family[- ]owned|family[- ]run|trusted by|"
    r"\d+ (?:happy )?(?:customers|clients)|five[- ]star|5[- ]star)\b",
    re.IGNORECASE)


def unsupported(page: str, material: Material) -> list[str]:
    """Claims on the page that nothing in the material supports.

    Generic copy is fine. A specific assertion about the business is not,
    unless it came from their own words or a quoted review.
    """
    own_words = " ".join(str(x) for x in (
        material.tagline or "", material.about or "",
        " ".join(material.services), " ".join(material.products),
        " ".join(str(i.get("name", "")) for i in material.menu_items),
        " ".join(str(q.get("text", "")) for q in material.quotes))).lower()
    text = re.sub(r"<script[^>]*>.*?</script>", " ", page, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return [claim for claim in {m.group(0) for m in _CLAIM_RE.finditer(text)}
            if claim.lower() not in own_words]
