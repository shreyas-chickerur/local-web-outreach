"""How the name is SET — size, case, alignment, tracking. Not which typeface.

Axis two, and it is here on evidence rather than on the ordering.
`agreement.unreachable()` reported two comparisons no reweighting of the eight
existing axes could ever order correctly: `hvac` and `roofer`, judged one
studio, ranked further apart than two pairs judged two studios. The axes the
vector counted where the judge did not were `accent` and `hero_subject` —
colour and subject, the two the judging rule says cannot alone make a different
site. What the judge WAS reading, in their own words, was "the same page with
and without a picture strip: heavy condensed dark type on a pale ground". The
vector had no way to say that.

    QUIET       moderate display size, sentence case, flush left, normal
                tracking. What every page does now, named so it stops being
                the absence of a decision.
    BANNER      the name at the largest size the screen will take, tight
                leading and slightly negative tracking. Needs a short name.
    STAMPED     uppercase, heavy, tight. Reads as a trade or a workshop.
    WIDE        uppercase at moderate size with the letters opened right out.
                Reads as a boutique or a studio; needs a short name.
    CENTRED     the whole first screen centred rather than flush left. The one
                treatment that changes the geometry rather than the letters.

The typeface PAIR is deliberately not here. That is a `identity.py` concern and
a later item in §2.1, and mixing the two would make one axis carry two
decisions — which is how `layout_bias` came to be a pure function of `mood`.

Nothing here decides WHICH treatment; `identity.py` does. This module owns what
each one means and what a business can support, so the axis can be proven to
manifest before anything is asked to choose between them.
"""

from __future__ import annotations

from app.site.render import Material

# Ordered. The fingerprint compares positionally and the census prints them.
TREATMENTS: tuple[str, ...] = ("quiet", "banner", "stamped", "wide", "centred")

DEFAULT = "quiet"

# Set in capitals with the letters opened out, a name stops fitting long before
# it does set flush left in sentence case. These are the widths at which each
# treatment stays on two lines at 1440 — past them the name wraps to three and
# the first screen turns into a wall.
LONGEST_FOR_BANNER = 24
LONGEST_FOR_WIDE = 18


def available(m: Material) -> list[str]:
    """The treatments this business's name can actually carry.

    The constraint is the NAME, not the photographs — which is what makes this
    a different kind of availability from `firstscreen.available` and worth
    stating rather than assuming. "Milestone Electric Air Plumbing" cannot be
    set in opened-out capitals; "Ichika" can be set any way at all.
    """
    name = (m.name or "").strip()
    can = ["quiet", "stamped", "centred"]
    if len(name) <= LONGEST_FOR_BANNER:
        can.append("banner")
    if len(name) <= LONGEST_FOR_WIDE:
        can.append("wide")
    return [treatment for treatment in TREATMENTS if treatment in can]
