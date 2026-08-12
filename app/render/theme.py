"""Visual system for generated sites.

One palette per industry, each built as a deliberate pairing rather than a hue
swap: a deep near-black ink, a saturated accent with enough contrast to carry
solid buttons on both light and photographic backgrounds, and a warm/cool tint
for section banding.

Contrast is a hard requirement, not a preference. Buttons sitting on a photo get
a solid fill and a scrim behind them — an outlined button over an unpredictable
image is unreadable, which is exactly what the first pass got wrong.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    ink: str        # near-black body text / dark bands
    accent: str     # primary actions, numerals, rules
    accent_dark: str  # hover / pressed
    tint: str       # section banding
    sand: str       # secondary surface
    eyebrow: str    # small caps label above headlines


_PALETTES = {
    # Warm, appetite-forward: charcoal + ember.
    "restaurant": Palette(
        ink="#17110d", accent="#c2410c", accent_dark="#9a3412",
        tint="#fdf8f3", sand="#f6ede3", eyebrow="#a16207",
    ),
    # Trades: confident, clean, high-trust blue-slate.
    "service": Palette(
        ink="#0b1220", accent="#0b6bcb", accent_dark="#075299",
        tint="#f4f8fd", sand="#eaf1fa", eyebrow="#0369a1",
    ),
    "generic": Palette(
        ink="#0e1015", accent="#4f46e5", accent_dark="#3730a3",
        tint="#f6f6fb", sand="#eeeef8", eyebrow="#4338ca",
    ),
}


def palette_for(industry: str | None) -> Palette:
    return _PALETTES.get((industry or "generic").lower(), _PALETTES["generic"])


# Industry-appropriate eyebrow + closing copy. Generic enough to be true for any
# business in the category — never a claim about this specific one.
_VOICE = {
    "restaurant": ("Now serving", "Come hungry.", "Reserve a table"),
    "service": ("Local & dependable", "Let's get it sorted.", "Request a quote"),
    "generic": ("Locally owned", "Let's talk.", "Get in touch"),
}


def voice_for(industry: str | None) -> tuple[str, str, str]:
    """(eyebrow, closing headline, primary CTA label) for an industry."""
    return _VOICE.get((industry or "generic").lower(), _VOICE["generic"])
