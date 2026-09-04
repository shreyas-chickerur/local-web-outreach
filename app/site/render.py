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
from dataclasses import dataclass, replace
from dataclasses import field as dc_field
from urllib.parse import quote_plus

from app.adapters.imageinfo import measure
from app.site.density import calculate_density_signal, density_attrs
from app.site.plan import (
    NO_DATA,
    RAISED,
    SECTION_RULES,
    PlannedSection,
    SitePlan,
    apply_order,
    plan_density,
)
from app.site.spec import SiteSpec, parse_spec
from app.site.styles import css, script
from app.site.theme import Theme, theme_for
from app.store.photos import rank_for_hero
from app.workbench.hours import parse_week

# Sections in the order they read, when nothing asks otherwise.
ORDER = ("hero", "stats", "recognition", "services", "menu", "gallery",
         "about", "features", "partners", "reviews", "hours", "contact")

# How the photo pool is divided. The hero always takes index 0. The offer cards
# take a run after it, but never so many that the gallery drops below the three
# tiles that make it worth having — a business with six photos should get both
# sections, not one section twice.
OFFER_ART_START = 1
OFFER_ART_MAX = 4
GALLERY_MIN = 3
# Proxied photos are served by us, so measuring one needs an absolute URL.
LOCAL = "http://127.0.0.1:8099"
GALLERY_MAX = 12

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
    # Sections lifted whole from their page, so a site with a Philosophy or a
    # partners list keeps them instead of losing them to our fixed layout.
    blocks: tuple[dict, ...] = ()
    # {url: what it shows}, said by a person. Empty until someone labels.
    photo_labels: dict = dc_field(default_factory=dict)
    # What each photograph shows, in the operator's words. Becomes alt text,
    # which every generated image had been shipping empty.
    photo_notes: dict = dc_field(default_factory=dict)
    trade_kind: str = "default"
    # Photographs already placed. Sections spend from one pool, so the same
    # picture cannot turn up in the gallery and again beside a feature row.
    spent: set = dc_field(default_factory=set)

    def take(self, urls, limit: int) -> list[str]:
        """Unspent photographs, marked as spent."""
        picked = []
        for url in urls:
            if url in self.spent:
                continue
            self.spent.add(url)
            picked.append(url)
            if len(picked) >= limit:
                break
        return picked

    def blocks_of(self, kind: str) -> tuple[dict, ...]:
        return tuple(b for b in self.blocks if b.get("kind") == kind)

    def photo_plan(self, offer_count: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """(offer art, gallery shots) — disjoint, and sized to the pool.

        Sections used to slice from index 1 independently, so the offer cards
        and the gallery showed the same four pictures, which reads as a site
        with four photos padded out twice. Splitting them naively then starved
        the gallery on a business with only six, so the offers yield first.
        """
        pool = self.images
        spare = max(0, len(pool) - OFFER_ART_START - GALLERY_MIN)
        take = min(offer_count, OFFER_ART_MAX, spare)
        offers = pool[OFFER_ART_START:OFFER_ART_START + take]
        gallery = pool[OFFER_ART_START + take:OFFER_ART_START + take + GALLERY_MAX]
        return offers, gallery

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
        blocks=tuple(published.get("blocks") or ()),
        photo_labels=dict(brief.get("photo_labels") or {}),
        photo_notes=dict(brief.get("photo_notes") or {}),
        trade_kind=trade_kind(brief.get("trade")),
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
        label = spec.cta_label or _CTA_LABEL.get(spec.cta or "call", "Call us")
        if spec.cta in (None, "call") and not spec.cta_label:
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


_FOOD_WORDS = ("restaurant", "cafe", "coffee", "bakery", "bar", "pizza",
               "barbecue", "grill", "diner", "kitchen", "food", "deli")
_TRADE_WORDS = ("contractor", "roofing", "plumb", "electric", "landscap",
                "lawn", "hvac", "construction", "repair", "cleaning")


def trade_kind(trade: str | None) -> str:
    """Which hero preference applies. A roofer leads with finished work; a
    restaurant leads with a plate or the room."""
    name = (trade or "").lower()
    if any(word in name for word in _FOOD_WORDS):
        return "food"
    if any(word in name for word in _TRADE_WORDS):
        return "trade"
    return "default"


def pick_hero(images: tuple[str, ...], offset: int = 0,
              labels: dict | None = None, trade: str = "default") -> str | None:
    """The lead photograph: landscape if we can tell, and honouring an offset.

    Shape is measurable, so a portrait crop never leads. Subject matter is not —
    a landscape photograph of raw peppers is still the wrong hero for a fine
    dining room, and nothing here can see that. `offset` exists because the
    operator can, and "use the next photo" is a one-word correction.
    """
    if not images:
        return None
    landscape: list[str] = []
    for url in images[:10]:
        size = measure(url if url.startswith("http") else f"{LOCAL}{url}")
        if size and size[1] and size[0] / size[1] >= 1.15:
            landscape.append(url)
    ordered = landscape or list(images)
    # A person's judgement outranks the machine's: shape only narrows the
    # field, the label decides which of them leads.
    if labels:
        ordered = rank_for_hero(ordered, labels, trade)
    return ordered[offset % len(ordered)]


def _hero(m: Material, spec: SiteSpec, t: Theme) -> str:
    photo = pick_hero(m.images, spec.hero_offset, m.photo_labels, m.trade_kind)
    if photo:
        m.spent.add(photo)
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


def _fills_rows(count: int) -> int:
    """How many cards to show so the last row is not one orphan.

    Four in a three-across grid leaves a single card alone under three, which
    looks broken rather than sparse.
    """
    if count <= 3:
        return count
    if count % 3 == 1:
        return count - 1        # 4 -> 3, 7 -> 6
    return min(count, 9)


def _offer_heading(m: Material) -> tuple[str, str]:
    """Name the section after what the business actually does."""
    trade = (m.trade or "").lower()
    if m.menu_items or any(word in trade for word in _FOOD_TRADES):
        return "On offer", "What we cook and serve"
    if m.products and not m.services:
        return "The shop", "What we make"
    return "What we do", "How we can help"


def _offer_item(item: str, index: int) -> str:
    """One offering, set as type.

    These used to carry a photograph each, paired by position — so "Online
    Ordering" got a night shot of the building and "Blackland Prairie Cuisine"
    got the same building again. A picture that has nothing to do with the
    words is worse than no picture, and the photographs are better used where
    they are actually about something: the gallery.
    """
    return (f'<article class="offer" data-reveal data-delay="{index % 4}">'
            f'<span class="idx">{index + 1:02d}</span><h3>{e(item)}</h3>'
            f'<span class="rule"></span></article>')


def _offer_row(item: str, index: int) -> str:
    """One offering in the sparse layout: a rule and a large line of type.

    Deliberately not a card. Two cards in a row built for four leave a gutter
    of dead space down the middle, which is the thing this layout exists to
    avoid.
    """
    return (f'<li data-reveal data-delay="{index % 4}">'
            f'<span class="idx">{index + 1:02d}</span>'
            f'<h3>{e(item)}</h3></li>')


def _services(m: Material, t: Theme) -> str:
    """What they offer, laid out according to how much of it there is.

    Three compositions rather than one grid with different numbers in it:

    * **sparse** (one or two) — an asymmetric split, display type carrying the
      left, the items set large against rules on the right. The auto-fit grid
      is not used at all here.
    * **balanced** (three) — three across, each still substantial.
    * **dense** (four or more) — the grid, which is genuinely right at volume.

    A section with nothing in it is absent, not empty: `renders` decides that
    and it is the same rule everywhere.
    """
    items = list(m.services) + list(m.products)
    signal = calculate_density_signal(items)
    if not signal["renders"]:
        return ""

    eyebrow, heading = _offer_heading(m)
    attrs = density_attrs(signal)
    lede = f'<p class="lede">{e(m.tagline)}</p>' if m.tagline else ""

    if signal["layout"] == "editorial":
        rows = "".join(_offer_row(item, i) for i, item in enumerate(items))
        # One photograph, large, rather than one per item: at this count a grid
        # of pictures reads as padding.
        art = (f'<div class="editorial-art" data-reveal data-delay="1">'
               f'<img src="{e(m.take(m.images, 1)[0])}" alt="" loading="lazy"'
               f' decoding="async"></div>') if len(m.images) > 2 else ""
        return (f'<section id="services" {attrs}><div class="wrap">'
                f'<div class="offers offers-editorial">'
                f'<div class="display" data-reveal>'
                f'<p class="eyebrow">{e(eyebrow)}</p><h2>{e(heading)}</h2>{lede}</div>'
                f'<div class="offers-side"><ol class="listing">{rows}</ol>{art}</div>'
                f'</div></div></section>')

    # A row of four that leaves one card stranded on its own line reads as a
    # mistake. Show a number that fills its rows.
    shown = items[:_fills_rows(len(items))]
    cards = "".join(_offer_item(item, i) for i, item in enumerate(shown))
    return (f'<section id="services" {attrs}><div class="wrap">'
            f'<div class="head" data-reveal><p class="eyebrow">{e(eyebrow)}</p>'
            f'<h2>{e(heading)}</h2>{lede}</div>'
            f'<div class="offers">{cards}</div></div></section>')


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
    return (f'<section id="menu" data-ground="raise"><div class="wrap">'
            f'<p class="eyebrow" data-reveal>On the menu</p>'
            f'<h2 data-reveal>What we serve</h2>{filters}'
            f'<ul class="dishes">{"".join(rows)}</ul></div></section>')


def _gallery(m: Material, t: Theme) -> str:
    # Everything the hero did not take. The offer cards take none at all.
    shots = m.take(m.images, GALLERY_MAX)
    if len(shots) < 3:
        return ""
    tiles = "".join(
        f'<button aria-label="Open photo {i + 1}" data-reveal data-delay="{i % 4}">'
        f'<img src="{e(src)}" alt="{e(m.photo_notes.get(src, ""))}"'
        f' loading="lazy" decoding="async"></button>'
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
    return (f'<section id="reviews" data-ground="raise"><div class="wrap">'
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
    """Their own words, set as prose rather than dropped in as a block.

    A paragraph in the body face at body size under a heading that says "Our
    story" looks like filler even when the words are good. Editorial treatment
    — an opening line pulled up into the display face, a drop cap, and a
    measure that is actually readable — is most of what makes copy look
    deliberate.
    """
    # Their own headed section beats our best guess at a paragraph: a block
    # titled "Philosophy" is the page telling us which words are the story.
    story = m.blocks_of("story")
    text = story[0]["text"] if story else m.about
    if not text:
        return ""
    heading = (story[0]["heading"] if story
               else "Our story" if _HISTORY.search(text) else "What we are about")
    m = replace(m, about=text)

    # Split off the first sentence to set as a standfirst. Falls back to the
    # whole text when there is only one sentence, which is common.
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    opener = sentences[0] if len(sentences) > 1 else ""
    rest = " ".join(sentences[1:]) if opener else text

    standfirst = (f'<p class="standfirst" data-reveal>{e(opener)}</p>'
                  if opener else "")
    body = (f'<p class="prose{" dropcap" if not opener else ""}" data-reveal '
            f'data-delay="1">{e(rest)}</p>') if rest else ""
    return (f'<section id="about"><div class="wrap"><div class="split">'
            f'<div data-reveal><p class="eyebrow">About</p><h2>{e(heading)}</h2>'
            f'<span class="flourish"></span></div>'
            f'<div class="story">{standfirst}{body}</div>'
            f'</div></div></section>')


# A badge, seal or laurel — not simply a photograph that happened to sit near
# the award heading in the markup. Heritage Table's award block contains
# Short-Rib.jpg and garden-tomatoes.jpg; showing those as laurels implies the
# tomatoes won something.
_BADGE_RE = re.compile(
    r"(award|badge|laurel|seal|medal|winner|winners|nominee|beard|"
    r"best-of|bestof|certified|rated|accredit)", re.IGNORECASE)


def _recognition(m: Material, t: Theme) -> str:
    """An award, stated once and large.

    Their own page leads with it, and it is the single most persuasive thing on
    the site — a James Beard nomination is not a bullet point.
    """
    awards = m.blocks_of("award")
    if not awards:
        return ""
    block = awards[0]
    kicker = block.get("kicker") or "Recognition"
    line = block["heading"]
    detail = block["text"].strip()
    badges = [src for src in block.get("images", ()) if _BADGE_RE.search(src)]
    art = ""
    if badges:
        art = "".join(f'<img src="{e(src)}" alt="" loading="lazy">'
                      for src in badges[:3])
        art = f'<div class="laurels" data-reveal data-delay="2">{art}</div>'
    # Supporting proof, but only what we already established elsewhere.
    proof = ""
    if m.rating and m.reviews:
        proof = (f'<p class="proof">{e(m.rating)} stars across '
                 f'{e(m.reviews)} Google reviews</p>')
    aside = "".join(part for part in (
        (f'<p class="accolade-note">{e(detail)}</p>' if detail else ""), proof, art))
    return (f'<section id="recognition" class="accolade-band" data-ground="raise">'
            f'<div class="wrap"><div class="accolade-grid">'
            f'<div data-reveal><p class="eyebrow">{e(kicker)}</p>'
            f'<h2 class="accolade">{e(line)}</h2></div>'
            f'<aside data-reveal data-delay="2">{aside}</aside>'
            f'</div></div></section>')


def _partners(m: Material, t: Theme) -> str:
    """Who they buy from, as a moving strip.

    A restaurant that lists fourteen farms is telling you what it is. Set as a
    marquee because the list is the point, not any one name in it.
    """
    groups = m.blocks_of("partners")
    if not groups or len(groups[0].get("entries") or ()) < 3:
        return ""
    block = groups[0]
    entries = block["entries"]
    def cell(entry: dict) -> str:
        note = f'<span class="note">{e(entry["note"])}</span>' if entry.get("note") else ""
        return f'<li><span class="who">{e(entry["name"])}</span>{note}</li>'
    # Doubled so the strip can loop without a visible seam.
    run = "".join(cell(x) for x in entries) * 2
    return (f'<section id="partners"><div class="wrap">'
            f'<p class="eyebrow" data-reveal>Sourcing</p>'
            f'<h2 data-reveal>{e(block["heading"])}</h2></div>'
            f'<div class="marquee" data-reveal data-delay="1">'
            f'<ul style="--n:{len(entries)}">{run}</ul></div></section>')


_WORD_RE = re.compile(r"[a-z]{4,}")
_IMAGE_STOP = frozenset({"jpeg", "jpg", "png", "webp", "scaled", "final",
                         "copy", "edit", "photo", "image", "small", "large",
                         "wide", "crop", "web", "site", "home", "new"})


def justified(image_url: str, *context: str) -> bool:
    """Does this picture name something in the block it would sit beside?

    Placement used to be positional, so a press-logo screenshot ended up
    illustrating "Dinner Service" and a photograph of a sandwich illustrated a
    coffee roaster. Requiring the filename to share a word with the heading or
    the copy is a low bar, but it is a real one — and it is the difference
    between a picture that belongs and one that merely fits.
    """
    name = image_url.rsplit("/", 1)[-1].lower()
    words = {w for w in _WORD_RE.findall(name) if w not in _IMAGE_STOP}
    if not words:
        return False
    haystack = " ".join(context).lower()
    return any(word in haystack or word.rstrip("s") in haystack for word in words)


def _features(m: Material, t: Theme) -> str:
    """Anything else their page had a section for, kept as alternating rows."""
    keep = [b for b in m.blocks
            if b.get("kind") in ("feature", "events", "press")
            and len(b.get("text", "").split()) >= 18]
    if not keep:
        return ""
    rows = []
    for i, block in enumerate(keep[:4]):
        relevant = [src for src in (block.get("images") or ())
                    if justified(src, block["heading"], block["text"])]
        fresh = m.take(relevant, 1)
        art = (f'<div class="shot"><img src="{e(fresh[0])}"'
               f' alt="{e(m.photo_notes.get(fresh[0], ""))}"'
               f' loading="lazy" decoding="async"></div>') if fresh else ""
        # Shape follows the count, not the index. A single row in the "wide"
        # shape stacks a 21:9 picture above three lines of text and occupies
        # 930px to say one thing; side by side it says the same thing in a
        # third of the height. With several rows the shapes vary — deliberately
        # not a left/right zig-zag, which is the most recognisable template
        # rhythm there is.
        if len(keep) == 1:
            shape = "plain" if art else "narrow"
        else:
            shape = ("wide", "offset", "narrow", "plain")[i % 4]
        rows.append(
            f'<article class="feature {shape}" data-reveal>'
            f'<div class="words"><h3>{e(block["heading"])}</h3>'
            f'<p>{e(block["text"][:420])}</p></div>{art}</article>')

    return (f'<section id="more"><div class="wrap">{"".join(rows)}</div></section>')


def _hours(m: Material, t: Theme) -> str:
    if not m.hours:
        return ""
    week = json.dumps(parse_week(list(m.hours))).replace("'", "&#39;")
    rows = "".join(f"<li><span>{e(line)}</span></li>" for line in m.hours[:7])
    return (f'<section id="hours" data-ground="raise"><div class="wrap narrow">'
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


_BUILDERS = {
    "stats": _stats, "recognition": _recognition, "services": _services,
    "menu": _menu, "gallery": _gallery, "about": _about, "features": _features,
    "partners": _partners, "reviews": _reviews, "hours": _hours,
    "contact": _contact,
}

_NO_DATA = {
    "menu": "they publish no prices we could read — often the menu is a PDF or "
            "a photo",
    "gallery": "there are not enough photos to build one",
    "services": "their site does not list what they offer in a readable way",
    "reviews": "no reviews with text came back for them",
    "stats": "there are not enough numbers we can stand behind",
    "recognition": "no award or nomination is published on their site",
    "partners": "their site does not list who they buy from",
    "features": "their site has no other sections to carry over",
    "hours": "no source publishes their opening hours",
    "about": "their site has no about text",
    "contact": "we have no address, phone or email to show",
}


def _order(spec: SiteSpec, available: set[str]) -> list[str]:
    available = available - set(spec.suppress or ())
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
    spec = parse_spec(spec_text)
    return build_from_spec(brief, spec), spec


def plan_for(brief: dict, spec: SiteSpec) -> SitePlan:
    """Resolve everything the page will be, before any of it is emitted.

    Deliberately built by asking each section builder whether it has anything
    to say, rather than by re-implementing those conditions here — two copies
    of "does this business publish hours?" would drift apart within a week.
    """
    m = material_from_brief(brief)
    theme = theme_for(spec.mood)
    hero = pick_hero(m.images, spec.hero_offset, m.photo_labels, m.trade_kind)
    if hero:
        m.spent.add(hero)

    built = {key: builder(m, theme) for key, builder in _BUILDERS.items()}
    available = {key for key, html in built.items() if html}
    order = apply_order([k for k in ORDER if k != "hero" and k in available], spec)

    plan = SitePlan(name=m.name, mood=spec.mood, layout_bias=theme.layout_bias,
                    hero_photo=hero, hero_line=(m.tagline or m.about or ""),
                    cta_kind=spec.cta, cta_label=_cta_label(m, spec),
                    cta_href=_cta_href(m, spec))
    if m.rating and m.reviews:
        plan.hero_facts.append(f"{m.rating} stars, {m.reviews} Google reviews")
    if m.address:
        plan.hero_facts.append(m.address)

    partner_blocks = m.blocks_of("partners")
    partner_entries = (list(partner_blocks[0].get("entries") or ())
                       if partner_blocks else [])
    counts: dict[str, list] = {
        "services": list(m.services) + list(m.products),
        "menu": list(m.menu_items), "gallery": list(m.images),
        "reviews": list(m.quotes), "partners": partner_entries}
    headings = {key: (eyebrow, heading)
                for key, eyebrow, heading in SECTION_RULES}
    for key in order:
        eyebrow, heading = headings.get(key, ("", ""))
        if key == "services":
            eyebrow, heading = _offer_heading(m)
        items = counts.get(key, [])
        plan.sections.append(PlannedSection(
            key=key, eyebrow=eyebrow, heading=heading,
            density=plan_density(items) if items else {},
            items=items, ground="raise" if key in RAISED else "base",
            images=_section_images(built[key])))

    for asked in ([spec.lead_with] if spec.lead_with else []) + list(spec.emphasis or []):
        if asked and asked not in available:
            plan.dropped.append(f"{asked}: {NO_DATA.get(asked, 'no data')}")
    plan.unused_images = [url for url in m.images if url not in m.spent]
    return plan


def _section_images(html: str) -> list[str]:
    return re.findall(r'<img[^>]+src="([^"]+)"', html or "")


def _cta_label(m: Material, spec: SiteSpec) -> str:
    if not m.phone and not m.address:
        return ""
    if m.phone:
        return spec.cta_label or _CTA_LABEL.get(spec.cta or "call", "Call us")
    return "Find us"


def _cta_href(m: Material, spec: SiteSpec) -> str:
    if m.phone:
        return f"tel:{_digits(m.phone)}"
    if m.address:
        return _maps(m.address)
    return ""


def build_from_spec(brief: dict, spec: SiteSpec) -> str:
    """Render from an already-resolved configuration.

    The iteration pipeline resolves the spec itself, so it needs a way in that
    does not re-parse a sentence — and re-parsing would quietly discard
    everything carried over from earlier instructions.
    """
    m = material_from_brief(brief)
    theme = theme_for(spec.mood)

    sections = {key: builder(m, theme) for key, builder in _BUILDERS.items()}
    available = {"hero"} | {k for k, v in sections.items() if v}
    order = _order(spec, available)

    body = _hero(m, spec, theme)
    for key in order:
        if key != "hero":
            body += "\n" + sections[key]

    description = m.tagline or m.about or ""
    page = (
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
        + f'<link href="{theme.fonts_href}" rel="stylesheet">\n'
        + f"<style>{css(theme)}</style>\n{_schema(m)}</head>\n"
        + f'<body data-theme="{e(spec.mood)}" '
        + f'data-theme-layout="{e(theme.layout_bias)}">\n'
        + _nav(m, order, spec) + "\n" + body + "\n"
        + _callbar(m, spec) + "\n" + _footer(m)
        + f"\n<script>{script()}</script>\n</body></html>")
    return page


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
