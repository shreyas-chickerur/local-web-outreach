"""What occupies the first 820 pixels, and in what relationship.

The first axis, and first for a reason: two pages identical above the fold are
the same site to the owner being shown them. Page architecture carries more
total difference and is mostly below the fold, so it buys less visible change
per unit of work and comes later.

The evidence for putting it first is in `.reviews/sheet` — eleven fixtures,
every one of them a photograph behind white type flush left, and the two the
fingerprint calls closest are two law firms a stranger would not tell apart.
The generator has exactly one position on this axis today.

    PHOTO       a photograph behind type, scrimmed. What every site does now.
    TYPE        type alone on the theme's ground, no photograph. Already
                reachable — the hero floor produces it when every candidate
                was looked at and condemned — but never chosen.
    SPLIT       type and photograph each taking half, hard-edged.
    FACTS       the numbers first: rating, review count, years, the things a
                visitor is actually checking, with photography secondary.
    PROOF       licence, insurance, service area and a quote action leading.
                Photography secondary or absent. A trade-driven position no
                restaurant would ever use, and the one that separates a roofer
                from a steakhouse rather than separating two roofers.

Nothing here decides WHICH position; `identity.py` does that. This module owns
what each one means and how it renders, so the axis can be proven to manifest
before anything is asked to choose between them.
"""

from __future__ import annotations

from app.site.render import Material

# Ordered. The fingerprint compares positionally and the census prints them.
POSITIONS: tuple[str, ...] = ("photo", "type", "split", "facts", "proof")

DEFAULT = "photo"

# What each position needs before it can be chosen. A position that cannot be
# built from this business's material is not a choice, it is a broken page —
# the identity call is offered only what will actually render.
def available(m: Material, hero: str | None) -> list[str]:
    """The positions this business can actually support.

    `type` is always available: it needs nothing but a name, which is why it is
    the floor's answer when every photograph has been condemned.
    """
    can = ["type"]
    if hero:
        can.extend(("photo", "split"))
    if m.rating and m.reviews:
        can.append("facts")
    if _proof_points(m):
        can.append("proof")
    return [position for position in POSITIONS if position in can]


def _proof_points(m: Material) -> list[str]:
    """The things a visitor checks before ringing a contractor.

    Only corroborated material — this reads what is already on `Material`, so
    nothing here can introduce a claim. Slice C's trade profiles are what will
    hunt for licence numbers and service areas properly; until then it is what
    the directory established.
    """
    points: list[str] = []
    if m.rating and m.reviews:
        points.append(f"{m.rating} from {m.reviews} reviews")
    if m.address:
        points.append(m.address.split(",")[-2].strip()
                      if m.address.count(",") >= 2 else m.address)
    if m.hours:
        points.append(m.hours[0])
    return points
