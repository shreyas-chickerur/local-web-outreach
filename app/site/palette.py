"""A palette candidate sampled from a business's own photographs. `BRIEF` §2.2.

The cheapest convincing form of catering: a taqueria with cobalt walls should
get a cobalt site. The colours are not sampled here from raw pixels — that
work is already done. The vision pass records `dominant_colours` on every
photograph, up to four real hex values, strongest first, validated
(`app.adapters.vision._is_hex`) before they are ever trusted. Reading that
field is smaller and more honest than a second colour-extraction pipeline
over cached JPEG bytes, and it is what "sample dominant colours" already
means in this codebase's own vision schema.

A photograph the vision pass flagged `is_logo_or_badge` is the nearest thing
to a declared brand colour this system corroborates — no business site or
directory listing here carries an actual brand-colour field — so its
colours are offered first when one exists, ahead of the hero and gallery
shots §2.2 names by default.

Every sampled hex is mapped onto the SAME closed `ACCENT_NAMES` enum
`identity.py` already validates against, by hue distance against
`theme.ACCENT_TUNING`. Nothing here bypasses that validation or the
contrast repair `Theme.recoloured()` already does — a sampled candidate is
just a better-informed guess at which of the existing names to reach for,
never a new kind of value the rest of the system has not seen before.
"""

from __future__ import annotations

from app.site.render import Material
from app.site.theme import ACCENT_TUNING, _to_hsl

# Below this saturation a colour reads as a shadow or a highlight, not a
# decision — `dominant_colours` is often padded with near-black or near-white
# entries from a photograph's own contrast range, and naming one of those "the
# accent" would be reading noise as material.
MIN_SATURATION = 0.18

# The HSL saturation formula is numerically unstable near the ends of the
# lightness range: an off-white like #f5f5f0 (245,245,240) computes a
# saturation of 0.2 — above `MIN_SATURATION` — from a five-part channel
# difference nobody would call "a colour". Gated separately from saturation
# because the failure mode is specific to the extremes, not to low
# saturation generally.
MIN_LIGHTNESS = 0.10
MAX_LIGHTNESS = 0.88

# How many of a photograph's own listed colours to look at. `dominant_colours`
# is already ordered strongest-first, so anything past the first couple is
# background texture rather than what a person would call the photo's colour.
COLOURS_PER_PHOTO = 2

# How many gallery photographs to sample beyond the hero, per §2.2's own
# wording ("the best two or three").
GALLERY_SAMPLE = 3


# Entries whose own saturation multiplier is 0 — `grey` and `charcoal` are
# there so a THEME can ask for a neutral accent, not so a photograph's own
# saturated colour has somewhere neutral to fall into. A hex that clears
# `MIN_SATURATION` is by definition not neutral, and hue 0 is shared with
# `red`, so without this exclusion a warm reddish-brown could nearest-match
# to grey purely on hue distance and report a colour as no colour at all.
_NEUTRAL_NAMES = frozenset(
    name for name, (_, sat_scale, _) in ACCENT_TUNING.items()
    if sat_scale <= 0.05)


def _nearest_accent(hex_colour: str) -> str | None:
    """The named accent whose hue is closest to this colour's, or None if the
    colour is too washed out to count as a decision at all."""
    hue, sat, light = _to_hsl(hex_colour)
    if sat < MIN_SATURATION or not (MIN_LIGHTNESS <= light <= MAX_LIGHTNESS):
        return None
    named = {name: tuning for name, tuning in ACCENT_TUNING.items()
             if name not in _NEUTRAL_NAMES}
    return min(
        named,
        key=lambda name: min(abs(named[name][0] - hue),
                             360 - abs(named[name][0] - hue)))


def _candidate_photos(material: Material, hero: str | None) -> list[str]:
    """Which photographs to read colours from, and in what order of trust.

    A logo/badge photo first — the closest thing to a declared brand colour
    this system has. Then the hero, because it is what the business already
    leads with. Then the best few gallery shots by the same quality signal
    `pick_hero` itself reads, so a blurry or dim photograph does not get to
    name the palette.
    """
    vision = material.photo_vision or {}
    logos = [url for url in material.images
            if (vision.get(url) or {}).get("is_logo_or_badge")]
    ranked = sorted(
        (url for url in material.images if url not in logos),
        key=lambda url: (vision.get(url) or {}).get("quality", 0),
        reverse=True)
    ordered = logos[:1]
    if hero and hero not in ordered:
        ordered.append(hero)
    for url in ranked:
        if len(ordered) >= 1 + 1 + GALLERY_SAMPLE:
            break
        if url not in ordered:
            ordered.append(url)
    return ordered


def sample_accents(material: Material, hero: str | None) -> list[str]:
    """Accent names worth offering as grounded in this business's own
    photographs, strongest candidate first. Empty when there is no vision
    data to read — everything degrades without a key, and this is one more
    thing that does.
    """
    vision = material.photo_vision or {}
    found: list[str] = []
    for url in _candidate_photos(material, hero):
        entry = vision.get(url) or {}
        for hexvalue in list(entry.get("dominant_colours") or [])[:COLOURS_PER_PHOTO]:
            name = _nearest_accent(str(hexvalue))
            if name and name not in found:
                found.append(name)
    return found
