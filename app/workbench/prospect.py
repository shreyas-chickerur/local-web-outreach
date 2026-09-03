"""How good a lead is this, and why.

Two different questions get confused here, so they stay separate:

* **Confidence** is how sure we are the data is right.
* **Prospect score** is how worth visiting the business is.

They pull in opposite directions — a business with no website at all is a
prime prospect *and* has almost nothing we can confirm — so a single number
would hide the thing you actually want to know. The score is a heuristic, not a
measurement, which is why every point of it comes with the reason attached: if
you disagree with a reason you can ignore the number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Every rule is (points, reason). Positive means "worth walking in".
NO_WEBSITE = 34
NOT_MOBILE = 26
NO_HTTPS = 14
THIN_SITE = 10
SITE_DOWN = 18
CHAIN = -45
CLOSED = -100
ESTABLISHED = 14
WELL_REVIEWED = 8
TOO_SMALL = -12
CONTACTABLE = 6
# A responsive, secure site with real content on it does not need replacing.
# Without this the score rewarded every large, healthy business — which is
# exactly the business least likely to hire you.
SITE_IS_FINE = -24


@dataclass
class Prospect:
    """A business we might visit, with the case for and against it."""

    name: str
    address: str | None = None
    website: str | None = None
    phone: str | None = None
    rating: float | None = None
    reviews: int | None = None
    category: str = ""
    summary: str | None = None
    source_url: str | None = None
    business_status: str | None = None
    is_chain: bool = False
    mobile_ready: bool | None = None
    https: bool | None = None
    site_reachable: bool | None = None
    thin_site: bool = False
    js_rendered: bool = False
    score: int = 0
    reasons: list[str] = field(default_factory=list)


def score(p: Prospect) -> Prospect:
    """Fill in `score` and `reasons`. Pure, so the rules stay arguable."""
    points = 50            # start neutral; the evidence moves it either way
    reasons: list[str] = []

    def add(delta: int, why: str) -> None:
        nonlocal points
        points += delta
        reasons.append(f"{'+' if delta > 0 else ''}{delta}  {why}")

    if (p.business_status or "").startswith("CLOSED"):
        add(CLOSED, "Google lists this business as closed")
        p.score, p.reasons = 0, reasons
        return p

    if p.is_chain:
        add(CHAIN, "several locations under this name — likely a chain")

    if not p.website:
        add(NO_WEBSITE, "no website at all")
    else:
        if p.site_reachable is False:
            add(SITE_DOWN, "their site does not load")
        if p.mobile_ready is False:
            add(NOT_MOBILE, "no viewport tag — the site is not built for phones")
        if p.https is False:
            add(NO_HTTPS, "still on http; browsers warn visitors about it")
        if p.js_rendered:
            # We received a shell, not a page. Claiming the site is empty would
            # be reporting our blind spot as their problem.
            reasons.append("  0  their site renders with JavaScript — we could "
                           "not read it, so judge this one by eye")
        elif p.thin_site:
            add(THIN_SITE, "the site publishes almost nothing to work with")
        if (not p.js_rendered and p.site_reachable is not False
                and p.mobile_ready is not False and p.https is not False
                and not p.thin_site):
            add(SITE_IS_FINE, "their site is already responsive, secure and full")

    if p.reviews is not None:
        if p.reviews >= 100:
            add(ESTABLISHED, f"{p.reviews} reviews — an established business")
        elif p.reviews < 10:
            add(TOO_SMALL, f"only {p.reviews} reviews — may be too new or too small")
    if p.rating is not None and p.rating >= 4.3 and (p.reviews or 0) >= 20:
        add(WELL_REVIEWED, f"{p.rating}★ — customers like them, so there is work to protect")
    if p.phone:
        add(CONTACTABLE, "a phone number to call ahead")

    p.score = max(0, min(100, points))
    p.reasons = reasons
    return p


def rank(prospects: list[Prospect]) -> list[Prospect]:
    """Best first. Ties break on review count: a bigger business is a bigger job."""
    return sorted((score(p) for p in prospects),
                  key=lambda p: (p.score, p.reviews or 0), reverse=True)
