"""What a trade actually needs, named in one place. BRIEF §5.

`_CTA_LABEL`/`_CTA_BY_TRADE` used to live in `render.py` with a comment saying
they belonged here once the trade profiles existed — this is that move, not a
new idea.

Three things per `trade_kind`, and this module is only the data:

* **the button's wording** (`cta_words`) — already built and tested, moved
  here whole;
* **which section a business leads its "what we do" content with, and what
  it's called** (`HEADING`) — a dentist's page and a roofer's page should not
  both say "How we can help" in the same breath they say nothing else alike;
* **a default section emphasis, used only when nothing more specific asked
  for one** (`DEFAULT_EMPHASIS`) — `SiteSpec.emphasis` from the identity call
  always wins; this is what a page gets when the model did not name one,
  which is not "no opinion", it is "the trade's own opinion".
* **which contractor facts are worth hunting for at all** (`FACT_HUNTS`) —
  `app/site/contractorfacts.py` only looks for a fact a trade could plausibly
  make. A restaurant does not carry a warranty and a dentist does not offer a
  free estimate; asking anyway is how a false positive gets in.
"""

from __future__ import annotations

# The button's wording, for this kind of action at this kind of business. A
# flat table per kind — "Book a table" is restaurant wording and it was
# reaching every business that resolved to `book`, including a dentist's page,
# which is the kind of thing an owner spots in one second and does not forget.
CTA_LABEL: dict[str, str] = {
    "call": "Call us", "book": "Book now", "order": "Order online",
    "quote": "Get a quote", "visit": "Find us",
}

CTA_BY_TRADE: dict[str, dict[str, str]] = {
    "food": {"book": "Book a table", "order": "Order online",
             "visit": "Find us"},
    "care": {"book": "Book an appointment", "call": "Call the practice"},
    "groom": {"book": "Book an appointment", "visit": "Find us"},
    "body": {"book": "Book a class", "visit": "Find us"},
    "desk": {"book": "Book a consultation", "call": "Call us",
             "quote": "Request a consultation"},
    "trade": {"book": "Book a visit", "quote": "Get a free estimate",
              "call": "Call us"},
    "retail": {"visit": "Find the shop", "order": "Shop online"},
}


def cta_words(kind: str, trade: str = "default") -> str:
    """The button's wording, for this kind of action at this kind of business."""
    per_trade = CTA_BY_TRADE.get(trade, {})
    return per_trade.get(kind) or CTA_LABEL.get(kind, "Call us")


# What the "what we do" section is called, per trade. Replaces a heading
# picked by two ad hoc conditions (food words in the trade string, products
# with no services) with one table covering every `trade_kind` the rest of the
# generator already sorts businesses into (`render.trade_kind`).
#
# `default` is what `render._offer_heading` always returned before this
# existed — kept as the fallback for a trade_kind the table has no opinion
# about, not deleted, so an unrecognised trade still gets a heading rather
# than an empty string.
HEADING: dict[str, tuple[str, str]] = {
    "food": ("On offer", "What we cook and serve"),
    "care": ("Treatments", "Ways we can help"),
    "groom": ("Services", "What we offer"),
    "body": ("Classes", "What we teach"),
    "desk": ("Practice areas", "How we can help"),
    "trade": ("Services", "What we handle"),
    "retail": ("The shop", "What we carry"),
    "default": ("What we do", "How we can help"),
}

# A shop that sells rather than serves gets a heading about the goods, not
# the service — this is about the SHAPE of the material (products with no
# services list), not the trade word, so it stays a rule layered over the
# table rather than a `retail` special case: a `trade` business that only
# lists products (a hardware counter with no listed "services") reads the
# same way a boutique does.
PRODUCTS_ONLY_HEADING = ("The shop", "What we make")


def heading_for(trade_kind: str, has_services: bool, has_products: bool) -> tuple[str, str]:
    """(eyebrow, heading) for the "what we do" section."""
    if has_products and not has_services:
        return PRODUCTS_ONLY_HEADING
    return HEADING.get(trade_kind, HEADING["default"])


# Which sections a trade leans on hardest, absent a more specific instruction.
# `plan.apply_order` already applies `spec.lead_with` and `spec.emphasis` from
# the identity call — those are a decision about THIS business and always
# win. This is what a page gets when the call named neither: a trade's own
# default rather than the raw alphabetical/registration order every trade
# would otherwise share.
#
# Deliberately short — two or three sections, not a full reordering. A long
# list here would compete with the model's own judgement about a specific
# business instead of filling the gap it left.
DEFAULT_EMPHASIS: dict[str, tuple[str, ...]] = {
    "food": ("gallery", "menu"),
    "care": ("reviews", "stats"),
    "groom": ("gallery", "reviews"),
    "body": ("gallery", "services"),
    "desk": ("stats", "reviews"),
    "trade": ("stats", "services"),
    "retail": ("gallery", "services"),
}


def emphasis_for(trade_kind: str) -> tuple[str, ...]:
    """The trade's own default emphasis — used only as a fallback."""
    return DEFAULT_EMPHASIS.get(trade_kind, ())


# Which of `app.site.contractorfacts.FACTS` are worth even looking for. Only
# `trade` carries all four today (BRIEF §5's contractor sections); the rest
# get none, which keeps a restaurant's "about" paragraph from being mined for
# a warranty it was never going to mention. Widening this to another
# `trade_kind` is a one-line change once that trade's own material is looked
# at directly rather than assumed to overlap with a contractor's.
FACT_HUNTS: dict[str, tuple[str, ...]] = {
    "trade": ("licensed_insured", "emergency", "warranty", "free_estimate"),
}


def facts_for(trade_kind: str) -> tuple[str, ...]:
    return FACT_HUNTS.get(trade_kind, ())
