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
#
# `layout_bias` is deliberately absent. It is a pure function of `mood` — six
# moods onto four biases, and nothing else can set it — so it can never differ
# when mood matches, and whenever mood crosses a bias boundary it counts the
# same decision twice. One decision, one axis. It comes back the moment Slice B
# makes page architecture independently settable, which is what it was always
# standing in for.
AXES: tuple[str, ...] = (
    "mood",
    "accent",
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
    {"leads_with", "section_order", "compositions"})

# What each axis is worth in the distance, from two separate principles that
# happen to agree today and will not once Slice B lands.
#
# VISIBILITY — how much of the difference a person actually sees, and where.
# The first screen is what the owner looks at when the laptop is turned around;
# a difference that only appears on scroll is worth less, and one nobody ever
# sees is worth nothing.
#
# DECIDEDNESS — whether the difference came from a designer or from what the
# business happens to publish. `section_order` and `compositions` rank low here
# rather than on visibility: a restaurant with a menu and one without are not
# two studios at work.
#
# These correlate across the eight axes below, so one ordering would serve
# today. Slice B breaks that: photographic treatment is highly visible AND
# material-driven — a business with three good photographs and one with none
# will differ there whatever anyone decided.
#
# WHEN THEY DISAGREE, DECIDEDNESS WINS, which is what `min` encodes. The vector
# measures design decisions, and a consequence of the brief is not one.
VISIBILITY: dict[str, float] = {
    "mood": 2.0,             # the whole feel, and the first thing on screen
    "accent": 1.0,           # immediate, but only paint
    "hero_subject": 1.5,     # the largest thing above the fold
    "action": 1.0,           # a button, above the fold, small
    "leads_with": 1.0,       # which band comes first: seen on scroll
    "section_order": 1.0,    # seen on scroll
    "compositions": 1.0,     # seen on scroll
}

DECIDEDNESS: dict[str, float] = {
    "mood": 2.0,             # chosen outright
    "accent": 2.0,           # chosen outright
    "hero_subject": 1.5,     # chosen, from what they happen to have
    "action": 2.0,           # chosen outright
    "leads_with": 2.0,       # chosen outright
    "section_order": 0.5,    # mostly what they publish
    "compositions": 0.5,     # mostly what they publish
}


def weight_of(axis: str) -> float:
    """What one axis contributes to the distance.

    The weaker of the two principles caps it, so an axis that is invisible or
    undecided counts for little however well it scores on the other.

    `min` IS THE SAFE CHOICE TODAY AND WILL BE WRONG. The vector's known
    failure is overstating difference, and capping suppresses — so it errs in
    the direction of the error we have. But it also suppresses a strong,
    deliberate choice that happens to sit below the fold, and the signature
    device is exactly that: high decidedness, often below the fold, one per
    site and the thing a person remembers about it. That is the axis where the
    two principles disagree in the other direction.

    Revisit when the signature device lands rather than inheriting this by
    default. `min` is a decision for the shape of the vector today, not a law.
    """
    return min(VISIBILITY.get(axis, 1.0), DECIDEDNESS.get(axis, 1.0))


def metric_version() -> str:
    """What the numbers were measured with.

    A distance is only comparable to another taken the same way, and this has
    gone wrong twice: once when the corpus changed underneath a pinned
    baseline, and once when the distance became weighted while the baseline
    stayed flat and the census reported "12% WORSE" against a change of ruler.

    So the baseline records this and the census refuses to compare across a
    change. Derived from the axes and both weightings, so it moves on its own.
    """
    import hashlib
    material = "|".join(
        f"{axis}={VISIBILITY.get(axis, 1.0)}/{DECIDEDNESS.get(axis, 1.0)}"
        for axis in AXES)
    return hashlib.sha256(material.encode()).hexdigest()[:8]


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
        "leads_with": str(spec.lead_with or (sections[0] if sections else "-")),
        # The set, not the order, so a reshuffle and a different page are told
        # apart from each other.
        "section_order": ">".join(sections),
        # What each section was laid out as — SORTED, so this carries only the
        # compositions and not the order they appear in. Built in page order it
        # encoded `section_order` inside itself, and the two axes then rose and
        # fell together: one decision counted twice, exactly as `layout_bias`
        # did against `mood`.
        #
        # One value per section today because only `services` has alternatives.
        # Slice C is what gives this axis any range at all.
        "compositions": ";".join(sorted(
            f"{s.key}:{(s.density or {}).get('layout', 'none')}"
            for s in plan.sections)),
        "action": str(spec.cta or "none"),
        "hero_subject": hero_subject,
    })


def distance(one: Fingerprint, two: Fingerprint) -> float:
    """How different two sites are, from 0.0 (identical) to 1.0.

    Weighted, because a flat count made a different accent worth exactly as
    much as a different section order — and it made the section set, which is
    mostly a fact about the business, worth as much as anything the generator
    chose. See `VISIBILITY` and `DECIDEDNESS`.
    """
    moved = one.differs_from(two)
    total = sum(weight_of(axis) for axis in AXES)
    return sum(weight_of(axis) for axis in moved) / total


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
