"""The diversity budget: a site that repeats a recent one is rejected and re-decided.

`BRIEF` §2.5. Sameness is a defect class on the same footing as a contrast
failure — machine-detectable, measured on every build, gated. This is the gate.

It was deferred on the grounds that "with eight axes it would reject nearly
everything". That was true when it was written and stopped being true when the
first-screen contract landed: measured against the eleven fixtures on the
current vector, one same-trade pair in ten collides, not nine. The premise for
waiting was checked and had expired, so the gate is built before more axes are
added — otherwise each new axis ships into a pipeline already known not to
force variety, and every measurement after it is taken on a corpus where
nothing did.

Three stages, in order of preference:

1. **Ask again, naming what is taken.** "These choices are already in use;
   choose differently and say why" is an instruction a model can act on.
   "Be different" is not.
2. **Perturb deterministically.** When the retries are spent, move the site
   along one axis by a rule rather than by asking — same business, same
   answer, every time. A build must never hang, and a slightly worse site that
   ships beats a good one that does not.
3. **Give up and say so.** A site that cannot be made distinct is recorded as
   a collision rather than silently shipped as one, so the operator knows
   before the owner does.

Nothing here authors anything. It re-runs a decision that was already the
model's to make, with more information about what has already been used.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field

from app.adapters import claude
from app.site import fingerprint as fp
from app.site import firstscreen, opening
from app.site.pipeline import spec_from_config
from app.site.render import material_from_brief, plan_for
from app.store import fingerprints as store

# How many axes a new site must move on, and at least one of them structural.
# The brief's numbers. They are tuned against the corpus once there is one
# large enough to tune against — a few dozen real leads, not eleven fixtures.
REQUIRED_AXES = 4
# Asking twice is enough to tell "the model had a better answer and did not
# reach for it" from "this business genuinely has one shape". Beyond that the
# retries cost money to produce the same answer.
MAX_RETRIES = 2


@dataclass
class Decision:
    """A resolved design direction, and what it took to get there."""

    config: dict
    collided_with: list[dict] = field(default_factory=list)
    attempts: int = 1
    perturbed: str = ""
    unresolved: bool = False

    @property
    def clean(self) -> bool:
        return not self.collided_with and not self.perturbed


def print_of(brief: dict, config: dict) -> fp.Fingerprint:
    """The vector a config would produce for this business."""
    spec = spec_from_config(config)
    return fp.of(plan_for(brief, spec), spec, material_from_brief(brief))


def _taken(previous: list[dict], axis: str) -> set[str]:
    return {str(values.get(axis)) for values in previous if axis in values}


def perturb(brief: dict, config: dict, previous: list[dict]) -> tuple[dict, str]:
    """Move this site along one axis, by rule rather than by asking.

    Deterministic on purpose: the same business gets the same answer on every
    build, which is the replay invariant. It reaches for the first screen first
    because that is the axis a person sees soonest, and falls back to the
    accent because every business can take one.
    """
    material = material_from_brief(brief)
    hero = None
    try:
        from app.site.render import pick_hero

        hero = pick_hero(material.images, 0, material.photo_labels,
                         material.trade_kind, material.size_of,
                         material.photo_vision)
    except Exception:                                          # noqa: BLE001
        hero = None

    seed = int(hashlib.sha256(
        str(brief.get("name", "")).encode()).hexdigest()[:8], 16)

    offered = firstscreen.available(material, hero)
    used = _taken(previous, "first_screen")
    free = [p for p in offered if p not in used]
    if free and len(offered) > 1:
        choice = free[seed % len(free)]
        if choice != config.get("first_screen"):
            return {**config, "first_screen": choice}, "first_screen"

    from app.site.theme import ACCENT_NAMES

    unused = [name for name in ACCENT_NAMES
              if name not in _taken(previous, "accent")]
    if unused:
        return {**config, "accent": unused[seed % len(unused)]}, "accent"
    return config, ""


def decide(conn: sqlite3.Connection, lead_id: int, brief: dict) -> Decision:
    """One design direction that does not repeat a recent one.

    Returns the config to build from. A collision is not an error — it is a
    request for a different answer, and only an unresolvable one is reported.
    """
    config = opening.opening_spec(brief)

    # A replayed direction is already a resolved answer — the gate ran when it
    # was first decided. Re-gating it is re-asking by another name, and it
    # breaks the replay invariant twice over: it costs a model call a keyless
    # reviewer cannot make, and it makes the answer depend on the order the
    # corpus happens to be loaded in.
    if config.get("read_by") == "frozen":
        return Decision(config=config)

    previous = store.recent(conn, fp.metric_version(), exclude_lead=lead_id)
    if not previous:
        return Decision(config=config)

    prints = [fp.Fingerprint(values) for values in previous]
    for attempt in range(1, MAX_RETRIES + 2):
        hit = fp.collisions(print_of(brief, config), prints,
                            axes=REQUIRED_AXES)
        if not hit:
            return Decision(config=config, attempts=attempt)
        if attempt > MAX_RETRIES or not claude.available():
            # Without a key there is nobody to ask again, and asking would
            # fall through to the trade table — which is not a different
            # answer, it is a worse one. Perturbation is the degraded path,
            # and it still varies by business, which is what §2.6 requires.
            break
        # Name what is taken. The model can act on that; it cannot act on
        # "be different".
        shared = sorted({axis for _, moved in hit
                         for axis in fp.AXES if axis not in moved})
        config = opening.opening_spec(brief, avoid=_avoidance(shared, prints, hit))

    hit = fp.collisions(print_of(brief, config), prints, axes=REQUIRED_AXES)
    if not hit:
        return Decision(config=config, attempts=MAX_RETRIES + 1)

    moved, axis = perturb(brief, config, previous)
    remaining = fp.collisions(print_of(brief, moved), prints,
                              axes=REQUIRED_AXES)
    return Decision(config=moved, collided_with=[dict(p.values) for _, p in
                                                 zip(hit, prints, strict=False)],
                    attempts=MAX_RETRIES + 1, perturbed=axis,
                    unresolved=bool(remaining))


def _avoidance(shared: list[str], prints: list[fp.Fingerprint],
               hit: list[tuple[int, set[str]]]) -> str:
    """What to tell the model is already taken, in its own vocabulary."""
    lines = []
    for index, _ in hit:
        values = prints[index].values
        lines.append("  " + ", ".join(
            f"{axis}={values.get(axis)}" for axis in shared if axis in values))
    return ("A recent site already made these choices, and this one is too "
            "close to it:\n" + "\n".join(lines)
            + "\n\nChoose differently on at least one of them, and say why the "
              "new choice suits this business rather than picking at random.")
