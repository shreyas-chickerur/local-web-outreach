"""What a site decided, as a vector — so sameness is measurable.

A generator's characteristic failure is that its output is recognisable as its
output. The operator is selling the opposite: a site that looks like a person
looked at this business and made decisions about it. So sameness is a defect on
the same footing as a contrast failure — machine-detectable, measured on every
build, and gated — rather than a taste question left to whoever is reviewing.

**Computed from the decisions, never from the rendered page.** Hashing HTML
would score two structurally identical sites as different because the
businesses use different words, so the gate would pass everything while
reporting healthy numbers. The decisions are what a stranger would recognise;
the words are what makes them look superficially unalike.

Slice B's diversity budget imports the same function. Two definitions of the
fingerprint would drift apart inside a week, and the one that mattered would be
the one nobody was reading.
"""

from __future__ import annotations

from dataclasses import dataclass


# The axes a site's identity is a point in. Ordered, because the vector is
# compared positionally and printed under a screenshot in that order.
#
# Slice B adds the rest — page architecture, grid, colour structure, type
# system, photographic treatment, section edges, the signature device, motion,
# density. These are the ones the generator can currently take a position on,
# and naming the empty ones now would report diversity that does not exist.
def metric_version() -> str:
    """What the numbers were measured with.

    A distance is only comparable to another distance taken the same way, and
    this has now gone wrong twice: once when the corpus changed underneath a
    pinned baseline, and once when the distance became weighted and the census
    cheerfully reported "12% WORSE" against a number measured flat.

    So the baseline records this and the census refuses to compare across a
    change instead of reporting a difference that is really a change of ruler.
    Derived from the axes and their weights, so it moves on its own.
    """
    import hashlib
    material = "|".join(f"{axis}={WEIGHTS.get(axis, 1.0)}" for axis in AXES)
    return hashlib.sha256(material.encode()).hexdigest()[:8]


AXES: tuple[str, ...] = (
    "mood",
    "accent",
    "layout_bias",
    "leads_with",
    "section_order",
    "compositions",
    "action",
    "hero_subject",
)

# An axis whose difference is structural rather than cosmetic. Two sites that
# differ only on colour are the same site painted twice, so the budget requires
# at least one of these.
STRUCTURAL: frozenset[str] = frozenset(
    {"layout_bias", "leads_with", "section_order", "compositions"})

# What each axis is worth in the distance, and the weighting is by VISIBILITY
# rather than by the structural set above.
#
# The evidence is the pair a person called identical. `law` and `bare-trade`
# differ on three structural axes — leads_with, section_order, compositions —
# and look like the same page anyway, because all three are below the fold and
# all three are downstream of what the business happens to publish rather than
# of anything the generator decided. Weighting the structural set higher would
# have pushed that pair further apart and made the miss worse.
#
# So: what shows in the first screen counts most, because the first screen is
# what the owner sees when the laptop is turned around. What only appears on
# scroll counts less. What is decided by the business's own material rather
# than by the design counts least — a restaurant with no menu and one with a
# menu are not two studios at work.
WEIGHTS: dict[str, float] = {
    "mood": 2.0,             # the whole feel, and the first thing visible
    "accent": 1.0,           # visible immediately, but only paint
    "layout_bias": 2.0,      # a real decision, and it shows at the top
    "hero_subject": 1.5,     # the largest thing on the first screen
    "action": 1.0,           # a button, above the fold, small
    "leads_with": 1.0,       # which band comes first: seen on scroll
    "section_order": 0.5,    # mostly what they publish
    "compositions": 0.5,     # mostly what they publish
}


@dataclass(frozen=True)
class Fingerprint:
    """One site's position on every axis."""

    values: dict[str, str]

    def differs_from(self, other: Fingerprint) -> set[str]:
        return {axis for axis in AXES
                if self.values.get(axis) != other.values.get(axis)}

    def as_row(self) -> list[tuple[str, str]]:
        """For printing under a screenshot: the picture says two sites feel
        alike, and this says which axis collided."""
        return [(axis, self.values.get(axis, "-")) for axis in AXES]


def of(plan, spec, material=None) -> Fingerprint:
    """The fingerprint of one resolved site.

    Takes the plan and the spec — the decisions — rather than the page.
    """
    sections = [s.key for s in plan.sections]
    hero_subject = "-"
    if material is not None and plan.hero_photo:
        hero_subject = str(
            material.photo_labels.get(plan.hero_photo) or "unlabelled")
    return Fingerprint({
        "mood": str(spec.mood),
        "accent": str(spec.accent or "theme default"),
        "layout_bias": str(plan.layout_bias),
        "leads_with": str(spec.lead_with or (sections[0] if sections else "-")),
        # The set, not the order, so a reshuffle and a different page are told
        # apart from each other.
        "section_order": ">".join(sections),
        # What each section was laid out as. One value today because only
        # `services` has alternatives; Slice C is what gives this range.
        "compositions": ";".join(
            f"{s.key}:{(s.density or {}).get('layout', 'none')}"
            for s in plan.sections),
        "action": str(spec.cta or "none"),
        "hero_subject": hero_subject,
    })


def distance(one: Fingerprint, two: Fingerprint) -> float:
    """How different two sites are, from 0.0 (identical) to 1.0.

    Weighted, because a flat count made a different accent worth exactly as
    much as a different section order — and it made the section set, which is
    mostly a fact about the business, worth as much as anything the generator
    chose. See `WEIGHTS`.
    """
    moved = one.differs_from(two)
    total = sum(WEIGHTS.get(axis, 1.0) for axis in AXES)
    return sum(WEIGHTS.get(axis, 1.0) for axis in moved) / total


def collisions(candidate: Fingerprint, previous: list[Fingerprint],
               *, axes: int = 4) -> list[tuple[int, set[str]]]:
    """Which of the previous sites this one is too close to.

    Returns (index, the axes it *did* differ on) for each collision, so the
    retry prompt can name what is already taken rather than saying "be
    different".
    """
    found: list[tuple[int, set[str]]] = []
    for index, other in enumerate(previous):
        moved = candidate.differs_from(other)
        if len(moved) < axes or not (moved & STRUCTURAL):
            found.append((index, moved))
    return found
