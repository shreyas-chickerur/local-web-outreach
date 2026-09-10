"""BRIEF §5 (Slice E): what fills a hero with no single photograph
chosen to lead it. A preference ladder, never skipped for effect: their
own video, then a sequence built from their own stills, then an abstract
backdrop generated from the palette, licensed stock last.

Only reaches this decision at the `first-type` hero position — every
other position already shows a real, chosen photograph as its
background (`_hero`'s own `layers` logic) — so this only ever fires when
there is genuinely nothing single, static, and good enough to lead with.

Stock is the one rung with no source integrated. Reaching it returns
`Backdrop(kind="none")` rather than fabricating a source — refusing is
the same choice this project already made for every other kind of
missing evidence (BRIEF: "never guess a licence number"), not a gap
quietly left in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BackdropKind = Literal["video", "stills", "generated", "none"]


@dataclass(frozen=True)
class Backdrop:
    kind: BackdropKind
    # For "stills": their own photographs to cycle through, best first,
    # never one vision already condemned.
    stills: tuple[str, ...] = ()


def select_backdrop(m) -> Backdrop:
    """The ladder, top to bottom. Nothing here is a guess: a rung either
    has real material behind it or is skipped."""
    # Imported lazily: `render.py` calls `select_backdrop` from `_hero()`,
    # so a module-level import here would be circular.
    from app.site.render import hero_scores, looked_at_and_rejected

    # 1. Their own video. No extraction path gathers one yet (Slice E,
    # disclosed rather than silently absent) — `material.videos` exists
    # as a field for the day one does, and is empty on every fixture in
    # this corpus today.
    videos = tuple(getattr(m, "videos", ()) or ())
    if videos:
        return Backdrop(kind="video", stills=(videos[0],))

    # 2. A sequence of their own stills — real photographs, never one the
    # vision pass already condemned (the same floor `pick_hero` enforces
    # for the hero itself, so a backdrop sequence can never show what the
    # hero refused to lead with).
    scored = hero_scores(m.images, m.photo_labels, m.trade_kind, m.size_of,
                         m.photo_vision, own=frozenset(m.photos))
    usable = [s.url for s in scored if not looked_at_and_rejected(s)]
    if len(usable) >= 2:
        return Backdrop(kind="stills", stills=tuple(usable[:4]))

    # 3. An abstract backdrop generated from the palette — needs nothing
    # but the theme already decided, so it is always available. The rung
    # that actually fires for a business with no usable photography at
    # all (`threadbare`'s one photograph, vision-condemned).
    return Backdrop(kind="generated")
