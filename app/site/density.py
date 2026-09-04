"""How much content a section has, and what that should do to its layout.

A single responsive grid cannot serve both a business with nine services and
one with two. `repeat(auto-fit, minmax(260px, 1fr))` collapses its empty
tracks, so two items become two half-width slabs with a gutter of dead space
down the middle — the exact look of a template being fed too little.

The fix is to make content volume an explicit input to layout rather than an
accident of it. This module turns a collection into a signal; the renderer
picks markup from it and the stylesheet keys off it. Nothing here touches the
data itself, so the rule that missing data means an absent section is decided
in one place — `renders` — instead of being re-derived per section.

Deliberately a pure function of `len(items)`: same collection, same signal,
same page. The generator's determinism depends on it.
"""

from __future__ import annotations

from typing import Literal, TypedDict

Profile = Literal["empty", "sparse", "balanced", "dense"]
Layout = Literal["none", "editorial", "feature", "grid"]

# Where the bands sit. Two items can never fill a row of cards; four always can.
SPARSE_MAX = 2
BALANCED_AT = 3

# Type scales inversely with volume. Sparse copy has to carry the section on
# its own, so it gets set larger; a dense list is read as a list and wants to
# be quieter. These are multipliers on the existing clamp(), not replacements
# for it — the fluid range still does the responsive work.
MODIFIERS: dict[Profile, float] = {
    "empty": 1.0, "sparse": 1.25, "balanced": 1.0, "dense": 0.85,
}

LAYOUTS: dict[Profile, Layout] = {
    "empty": "none",         # render nothing at all
    "sparse": "editorial",   # asymmetric: display type against a short list
    "balanced": "feature",   # three across, each still substantial
    "dense": "grid",         # the auto-fit grid, which is right here
}


class Density(TypedDict):
    """The signal a section needs to lay itself out."""

    count: int
    profile: Profile
    modifier: float
    layout: Layout
    renders: bool


def profile_for(count: int) -> Profile:
    if count <= 0:
        return "empty"
    if count <= SPARSE_MAX:
        return "sparse"
    if count == BALANCED_AT:
        return "balanced"
    return "dense"


def calculate_density_signal(items: list) -> Density:
    """Classify a collection by volume.

    Takes the collection rather than a count so callers cannot disagree about
    what was counted — the thing being laid out is the thing being measured.
    """
    count = len(items)
    profile = profile_for(count)
    return {
        "count": count,
        "profile": profile,
        "modifier": MODIFIERS[profile],
        "layout": LAYOUTS[profile],
        "renders": profile != "empty",
    }


def density_attrs(signal: Density) -> str:
    """The hooks the stylesheet needs, as attributes on the section.

    `data-density` selects the layout — it is what lets the sparse case ban the
    auto-fit grid outright rather than tweak it. `--density-scale` rides along
    as a custom property so type can scale fluidly without a second breakpoint
    system: `calc(clamp(19px,1.9vw,25px) * var(--density-scale))`.
    """
    scale = f"{signal['modifier']:g}"
    return f'data-density="{signal["profile"]}" style="--density-scale:{scale}"'
