"""Phase 3, Step 2: one art-direction answer per business, closed-set
validated and repaired, never trusted as typed. `BRIEF` §3's own rule for
every model answer in this system — fenced as evidence, checked against a
closed set — applied to a NEW kind of answer: not a fact about the
business, a DESIGN decision about how to present it.

Every value here traces to something the brief or the vision pass already
recorded: `type_pair` is a name from `theme.TYPEFACE_PAIRS`; `accent` is a
name `palette.sample_accents()` (or the same closed `ACCENT_TUNING` table
it draws from) would recognise; `signature_device` must be one
`signature.available()` says this business's own material can carry.
Nothing here is generated from the trade alone — that is the "most
average site in the category" failure this round exists to fix (see
`.reviews/NEXT-ROUND.md`, Part B's own framing).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.site.theme import ACCENT_TUNING, TYPEFACE_PAIRS, contrast

PHOTO_TREATMENTS: tuple[str, ...] = (
    "full_bleed", "duotone", "framed", "vignette_scrim", "grid_mosaic",
)

SECTION_WEIGHTS: tuple[str, ...] = ("heavy", "light", "breathing")

# WCAG AA for normal text. Every art direction's ink/base and
# accent/base pairing must clear this or be repaired until it does —
# never shipped under it, whatever the sampled candidate first offered.
MIN_CONTRAST = 4.5


@dataclass(frozen=True)
class ArtDirection:
    business: str
    mood: str
    mood_why: str
    type_pair: str
    base: str
    ink: str
    accent: str
    accent_name: str
    photo_treatment: str
    signature_device: str
    signature_why: str
    section_rhythm: tuple[str, ...]
    content_hash: str = field(default="", compare=False)

    def to_json(self) -> dict:
        return asdict(self)


class ArtDirectionError(ValueError):
    pass


def validate(direction: ArtDirection, *, available_devices: tuple[str, ...]) -> None:
    """Raises if any value falls outside its closed set, or if a repair
    was needed and not applied before this was called — this is the
    check that runs AFTER `repair_contrast()`, not instead of it."""
    if direction.type_pair not in TYPEFACE_PAIRS:
        raise ArtDirectionError(f"{direction.type_pair!r} is not a named "
                                f"type pair in theme.TYPEFACE_PAIRS")
    if direction.accent_name not in ACCENT_TUNING:
        raise ArtDirectionError(f"{direction.accent_name!r} is not a named "
                                f"accent in theme.ACCENT_TUNING")
    if direction.photo_treatment not in PHOTO_TREATMENTS:
        raise ArtDirectionError(f"{direction.photo_treatment!r} is not a "
                                f"known photograph treatment")
    if direction.signature_device not in available_devices:
        raise ArtDirectionError(
            f"{direction.signature_device!r} is not in this business's own "
            f"available devices {available_devices!r} -- signature.py's "
            f"own material-backed check")
    if set(direction.section_rhythm) - set(SECTION_WEIGHTS):
        raise ArtDirectionError(f"{direction.section_rhythm!r} uses a "
                                f"weight outside {SECTION_WEIGHTS!r}")
    for a, b in zip(direction.section_rhythm, direction.section_rhythm[1:]):
        if a == b:
            raise ArtDirectionError(
                f"section_rhythm {direction.section_rhythm!r} repeats "
                f"{a!r} on two adjacent sections")
    if contrast(direction.ink, direction.base) < MIN_CONTRAST:
        raise ArtDirectionError(
            f"ink/base contrast {contrast(direction.ink, direction.base):.2f} "
            f"is under {MIN_CONTRAST} -- repair before validating")
    if contrast(direction.accent, direction.base) < MIN_CONTRAST:
        raise ArtDirectionError(
            f"accent/base contrast "
            f"{contrast(direction.accent, direction.base):.2f} is under "
            f"{MIN_CONTRAST} -- repair before validating")


def persisted_path(business: str) -> Path:
    return Path("tests/fixtures/design") / f"{business}.art-direction.json"


def persist(direction: ArtDirection) -> Path:
    """BRIEF §4's deterministic-replay invariant applied to this new kind
    of answer: written once, beside the brief, so a rebuild replays it
    rather than re-asking."""
    path = persisted_path(direction.business)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = direction.to_json()
    body = json.dumps({k: v for k, v in payload.items() if k != "content_hash"},
                      indent=2, sort_keys=True)
    payload["content_hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def load(business: str) -> ArtDirection:
    data = json.loads(persisted_path(business).read_text())
    data["section_rhythm"] = tuple(data["section_rhythm"])
    return ArtDirection(**data)
