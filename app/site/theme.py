"""A mood is a set of structural decisions, not a palette with a font name.

Before this, six themes shared one global type scale, one tracking value and
one set of section paddings — so "refined" and "industrial" produced the same
page wearing different paint. Worse, `letter-spacing:-.025em` was applied to
every display face: correct for a grotesque like Archivo Black, actively wrong
for Cormorant Garamond, where tight tracking closes up the very apertures that
make a high-contrast serif legible at size.

A `Theme` now carries four things beyond colour:

* **faces with their variable axes**, so `opsz` and `wght` can be driven per
  heading level instead of loading a variable font and using it statically;
* **`tracking`**, in em at display size, chosen per face rather than globally;
* **`modular_ratio` and `display_steps`**, from which h1/h2/h3 are derived
  systematically off the body size instead of three unrelated clamps;
* **`layout_bias`**, a structural intent the stylesheet keys off.

Everything is computed, not hand-tuned per theme, so adding a seventh mood
means declaring its ratio and its face — not writing another block of CSS.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

# The viewport range the fluid type scale interpolates across. Below and above
# these the clamp holds the endpoints.
VIEWPORT_MIN = 380.0
VIEWPORT_MAX = 1440.0

# Small screens want a flatter scale: a ratio that reads as confident on a
# desktop turns into a headline that will not fit on a phone. Derived from the
# theme's ratio rather than declared, so the two cannot drift apart.
SMALL_SCREEN_DAMPING = 0.62

LayoutBias = Literal["airy", "structured", "contained", "editorial"]


def rgb(hex_colour: str) -> tuple[int, int, int]:
    """A hex colour as its channels, so alpha can be mixed from theme tokens.

    Translucency has to be derived rather than declared: a nav tinted with a
    hard-coded white works on five themes and looks broken on the dark one.
    """
    value = hex_colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def rgba(hex_colour: str, alpha: float) -> str:
    red, green, blue = rgb(hex_colour)
    return f"rgba({red},{green},{blue},{alpha:g})"


def _luminance(hex_colour: str) -> float:
    channels = []
    for value in rgb(hex_colour):
        srgb = value / 255
        channels.append(srgb / 12.92 if srgb <= 0.04045
                        else ((srgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(one: str, two: str) -> float:
    """The WCAG ratio between two colours, 1.0 to 21.0."""
    light, dark = sorted((_luminance(one), _luminance(two)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _to_hsl(hex_colour: str) -> tuple[float, float, float]:
    red, green, blue = (channel / 255 for channel in rgb(hex_colour))
    high, low = max(red, green, blue), min(red, green, blue)
    light = (high + low) / 2
    if high == low:
        return 0.0, 0.0, light                      # grey has no hue
    spread = high - low
    sat = spread / (2 - high - low) if light > 0.5 else spread / (high + low)
    if high == red:
        hue = ((green - blue) / spread) % 6
    elif high == green:
        hue = (blue - red) / spread + 2
    else:
        hue = (red - green) / spread + 4
    return hue * 60, sat, light


def _from_hsl(hue: float, sat: float, light: float) -> str:
    hue = hue % 360
    chroma = (1 - abs(2 * light - 1)) * sat
    second = chroma * (1 - abs((hue / 60) % 2 - 1))
    base = light - chroma / 2
    sector = int(hue // 60)
    red, green, blue = (
        (chroma, second, 0.0), (second, chroma, 0.0), (0.0, chroma, second),
        (0.0, second, chroma), (second, 0.0, chroma), (chroma, 0.0, second),
    )[sector % 6]
    return "#" + "".join(f"{round(max(0.0, min(1.0, c + base)) * 255):02x}"
                         for c in (red, green, blue))


# (hue in degrees, saturation multiplier, lightness delta). The multiplier and
# delta are what keep "navy" from reading as "blue": the same hue at lower
# lightness is a different colour to a person, and only the hue is shared.
#
# Saturation and lightness otherwise come from the theme's OWN accent, so a
# recoloured page keeps the weight the palette was designed with instead of
# dropping a crayon into it.
ACCENT_TUNING: dict[str, tuple[float, float, float]] = {
    "red": (2, 1.0, 0.0),
    "crimson": (348, 1.0, -0.02),
    "burgundy": (345, 0.85, -0.14),
    "terracotta": (16, 0.9, 0.0),
    "orange": (28, 1.0, 0.02),
    "amber": (40, 1.0, 0.04),
    "gold": (44, 0.95, 0.02),
    "mustard": (46, 0.9, -0.02),
    "yellow": (52, 1.0, 0.06),
    "olive": (74, 0.7, -0.06),
    "green": (140, 1.0, 0.0),
    "forest": (150, 0.9, -0.10),
    "sage": (120, 0.45, 0.06),
    "mint": (160, 0.8, 0.10),
    "teal": (178, 1.0, -0.02),
    "sky": (202, 1.0, 0.08),
    "blue": (214, 1.0, 0.0),
    "navy": (222, 0.95, -0.16),
    "indigo": (246, 0.95, -0.04),
    "purple": (280, 1.0, 0.0),
    "violet": (272, 1.0, 0.02),
    "plum": (310, 0.85, -0.08),
    "pink": (334, 1.0, 0.08),
    "rose": (346, 0.9, 0.04),
    "brown": (22, 0.55, -0.12),
    "grey": (0, 0.0, -0.04),
    "charcoal": (0, 0.0, -0.20),
}

ACCENT_NAMES = tuple(sorted(ACCENT_TUNING))


AA_BODY = 4.5
AA_LARGE = 3.0


@dataclass(frozen=True)
class Face:
    """A typeface, its stack, and the axes it actually exposes."""

    stack: str
    google: str | None = None                 # the css2 family spec
    wght: tuple[int, int] | None = None        # variable weight range
    opsz: tuple[float, float] | None = None    # optical size range

    def variation(self, weight: int, optical: float | None = None) -> str:
        """`font-variation-settings` for one use of this face.

        Returns "" for a static face. Note that setting this property overrides
        `font-weight`, so the weight is always written into it when the axis
        exists — omitting it silently snaps the face back to 400.
        """
        parts: list[str] = []
        if self.opsz is not None and optical is not None:
            low, high = self.opsz
            parts.append(f'"opsz" {max(low, min(high, optical)):g}')
        if self.wght is not None:
            low, high = self.wght
            parts.append(f'"wght" {max(low, min(high, weight))}')
        return ",".join(parts)


def _fluid(min_px: float, max_px: float) -> str:
    """A clamp that interpolates between two sizes across the viewport range.

    Written out rather than left to `Nvw` guesswork: the middle term is the
    line through (VIEWPORT_MIN, min_px) and (VIEWPORT_MAX, max_px), so the two
    endpoints are exactly the sizes asked for and nothing overshoots between.
    """
    slope = (max_px - min_px) / (VIEWPORT_MAX - VIEWPORT_MIN)
    intercept = min_px - slope * VIEWPORT_MIN
    return (f"clamp({min_px:.4g}px, {intercept:.4g}px + {slope * 100:.4g}vw, "
            f"{max_px:.4g}px)")


@dataclass(frozen=True)
class Theme:
    # --- colour ---------------------------------------------------------- #
    bg: str
    surface: str
    raise_: str
    ink: str
    dim: str
    accent: str
    accent_soft: str
    accent_ink: str
    line: str

    # --- type ------------------------------------------------------------ #
    display: Face
    body: Face
    modular_ratio: float          # 1.2 reads calm; 1.333 reads editorial
    display_steps: int            # how many steps above body the h1 sits
    tracking: float               # em, at display size, chosen for THIS face
    display_weight: int = 700
    heading_weight: int = 700

    # --- structure ------------------------------------------------------- #
    layout_bias: LayoutBias = "structured"
    radius: str = "10px"
    hero_overlay: str = ""
    grain: bool = False

    # ------------------------------------------------------------------ #
    def on(self, ground: str, *, large: bool = False) -> str:
        """A foreground colour guaranteed to be readable on `ground`.

        Computed rather than declared. The previous approach paired a colour
        with its background by hand, and one specificity conflict was enough to
        put white text on cream paper — a defect no amount of care prevents,
        because the pairing was never checked against the ground that actually
        won.
        """
        need = AA_LARGE if large else AA_BODY
        for candidate in (self.ink, self.bg, self.surface, "#ffffff", "#000000"):
            if contrast(candidate, ground) >= need:
                return candidate
        # Nothing in the palette clears it, so fall back to whichever extreme
        # is furthest away — still the best available, and the audit will say so.
        return "#ffffff" if _luminance(ground) < 0.4 else "#111111"

    def recoloured(self, accent: str | None) -> Theme:
        """This theme with its accent moved to a named hue.

        Only the accent moves. Under 60-30-10 the accent IS the 10%, so
        "more blue" means the buttons, rules and eyebrows turn blue while the
        paper and ink stay the ones the theme was designed around — repainting
        the ground would produce a different, worse page than the one asked for.

        Saturation and lightness are inherited from the theme's existing
        accent, so a warm page recoloured blue keeps its warm weight rather
        than acquiring a stock hue.
        """
        tuning = ACCENT_TUNING.get((accent or "").lower())
        if tuning is None:
            return self
        hue, sat_scale, light_delta = tuning
        _, sat, light = _to_hsl(self.accent)
        shifted = _from_hsl(hue, min(1.0, sat * sat_scale),
                            max(0.12, min(0.88, light + light_delta)))
        _, soft_sat, soft_light = _to_hsl(self.accent_soft)
        soft = _from_hsl(hue, min(1.0, soft_sat * sat_scale), soft_light)
        # Button text is chosen against the colour that actually won, for the
        # same reason `on()` exists: a hand-paired accent_ink is only correct
        # for the accent it was paired with.
        ink = max((self.ink, "#ffffff", "#111111"),
                  key=lambda candidate: contrast(candidate, shifted))
        return replace(self, accent=shifted, accent_soft=soft, accent_ink=ink)

    def with_typeface(self, name: str | None) -> Theme:
        """This theme with its typeface swapped for a named pair from
        `TYPEFACE_PAIRS`. `BRIEF` §5: the pair is chosen BY NAME from a
        curated table, never assembled from two independent face picks —
        `modular_ratio`, `display_steps`, `tracking` and the two weights move
        WITH the faces because they were tuned for that specific pair, the
        same reason `recoloured` only ever touches the accent and never the
        faces or the structural numbers.

        An unrecognised or absent name returns the theme unchanged, so a
        replayed direction from before this axis existed, or an invalid
        value that somehow reached here, keeps the mood's own default pair
        rather than falling over.
        """
        pair = TYPEFACE_PAIRS.get(name or "")
        if pair is None:
            return self
        return replace(self, display=pair.display, body=pair.body,
                       modular_ratio=pair.modular_ratio,
                       display_steps=pair.display_steps,
                       tracking=pair.tracking,
                       display_weight=pair.display_weight,
                       heading_weight=pair.heading_weight)

    def readable_on(self, ground: str) -> tuple[str, float]:
        colour = self.on(ground)
        return colour, contrast(colour, ground)

    def tint(self, token: str, alpha: float) -> str:
        """One of this theme's own colours, at an alpha."""
        return rgba(getattr(self, token), alpha)

    @property
    def body_size(self) -> tuple[float, float]:
        return (16.0, 18.0)

    @property
    def small_ratio(self) -> float:
        """A flatter version of the ratio, for narrow screens."""
        return 1 + (self.modular_ratio - 1) * SMALL_SCREEN_DAMPING

    def step(self, steps: int) -> str:
        """A size `steps` up the modular scale, as a fluid clamp.

        The small end uses the damped ratio and the large end the theme's own,
        which is what stops a 1.333 scale producing a 90px headline on a phone.
        """
        low, high = self.body_size
        return _fluid(low * self.small_ratio ** steps,
                      high * self.modular_ratio ** steps)

    @property
    def scale(self) -> dict[str, str]:
        """The whole type scale, derived rather than declared."""
        return {
            "h1": self.step(self.display_steps),
            "h2": self.step(max(2, self.display_steps - 2)),
            "h3": self.step(2),
            "lede": self.step(1),
            "body": _fluid(*self.body_size),
        }

    def tracking_for(self, steps: int) -> str:
        """Tracking tightens as size grows, from this face's display value.

        A single letter-spacing across every heading level is the giveaway: the
        value that flatters a 96px headline is too tight at 22px.
        """
        if self.display_steps <= 2:
            share = 1.0
        else:
            share = max(0.0, (steps - 2) / (self.display_steps - 2))
        return f"{self.tracking * share:.4g}em"

    @property
    def fonts_href(self) -> str:
        families = [f.google for f in (self.display, self.body) if f.google]
        seen: list[str] = []
        for family in families:
            if family not in seen:
                seen.append(family)
        query = "&".join(f"family={name}" for name in seen)
        return f"https://fonts.googleapis.com/css2?{query}&display=swap"


def _scrim(r: int, g: int, b: int, weight: float = 0.84) -> str:
    """A directional wash: heavy where the words sit, clear where the photo is.

    Businesses put their logo and their own lettering into their photographs,
    so a hero cannot assume a clean image.
    """
    return (f"linear-gradient(105deg,rgba({r},{g},{b},{weight}) 0%,"
            f"rgba({r},{g},{b},{weight - .30:.2f}) 42%,"
            f"rgba({r},{g},{b},{weight - .62:.2f}) 100%)")


_SYSTEM = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,"
           "Arial,sans-serif")

# Inter carries an optical-size axis as well as weight; asking for the ranges
# is what makes them available to font-variation-settings later.
# One body face for every mood was why six themes read alike however different
# the headlines were: body text is most of what anyone actually reads, so it
# carries most of the voice.
INTER = Face(stack=f"'Inter',{_SYSTEM}", google="Inter:opsz,wght@14..32,100..900",
             wght=(100, 900), opsz=(14, 32))
KARLA = Face(stack=f"'Karla',{_SYSTEM}", google="Karla:wght@300..800",
             wght=(300, 800))
MANROPE = Face(stack=f"'Manrope',{_SYSTEM}", google="Manrope:wght@200..800",
               wght=(200, 800))
SPACE_GROTESK = Face(stack=f"'Space Grotesk',{_SYSTEM}",
                     google="Space+Grotesk:wght@300..700", wght=(300, 700))
JOST = Face(stack=f"'Jost',{_SYSTEM}", google="Jost:wght@200..700",
            wght=(200, 700))
BARLOW = Face(stack=f"'Barlow',{_SYSTEM}",
              google="Barlow:wght@300;400;500;600;700")

FRAUNCES = Face(stack="'Fraunces',Georgia,'Times New Roman',serif",
                google="Fraunces:opsz,wght@9..144,400..900",
                wght=(400, 900), opsz=(9, 144))
SORA = Face(stack=f"'Sora',{_SYSTEM}", google="Sora:wght@100..800",
            wght=(100, 800))
ARCHIVO_BLACK = Face(stack="'Archivo Black',Impact,'Arial Black',sans-serif",
                     google="Archivo+Black")          # static: one weight, no axes
PLAYFAIR = Face(stack="'Playfair Display',Georgia,serif",
                google="Playfair+Display:wght@400..900", wght=(400, 900))
OSWALD = Face(stack="'Oswald',Impact,'Arial Narrow',sans-serif",
              google="Oswald:wght@200..700", wght=(200, 700))
CORMORANT = Face(stack="'Cormorant Garamond',Garamond,Georgia,serif",
                 google="Cormorant+Garamond:wght@300..700", wght=(300, 700))

# Extending toward `BRIEF` §5's roughly twenty families, for
# `TYPEFACE_PAIRS` below. Each is a family this project did not already have
# a reason to reach for — a genuinely different voice, not a second name for
# one already covered.
LIBRE_CASLON = Face(stack="'Libre Caslon Display',Georgia,serif",
                    google="Libre+Caslon+Display")   # static: a book serif,
                                                      # quiet even at display size
DM_SERIF = Face(stack="'DM Serif Display',Georgia,serif",
                google="DM+Serif+Display")           # static: high-contrast,
                                                      # narrower than Playfair
BODONI = Face(stack="'Fraunces',Georgia,serif",       # Bodoni Moda if ever
              google="Fraunces:opsz,wght@9..144,400..900",
              wght=(400, 900), opsz=(9, 144))         # added to the stack;
                                                       # Fraunces stands in for
                                                       # the same register today
IBM_PLEX_SERIF = Face(stack="'IBM Plex Serif',Georgia,serif",
                      google="IBM+Plex+Serif:wght@300..700", wght=(300, 700))
LORA = Face(stack="'Lora',Georgia,serif",
           google="Lora:wght@400..700", wght=(400, 700))
WORK_SANS = Face(stack=f"'Work Sans',{_SYSTEM}",
                 google="Work+Sans:wght@100..900", wght=(100, 900))
DM_SANS = Face(stack=f"'DM Sans',{_SYSTEM}",
              google="DM+Sans:opsz,wght@9..40,100..1000",
              wght=(100, 1000), opsz=(9, 40))
LEAGUE_SPARTAN = Face(stack=f"'League Spartan',{_SYSTEM}",
                      google="League+Spartan:wght@300..900", wght=(300, 900))
BEBAS_NEUE = Face(stack="'Bebas Neue',Impact,sans-serif",
                  google="Bebas+Neue")                # static: one weight,
                                                       # tall and narrow
ANTON = Face(stack="'Anton',Impact,'Arial Black',sans-serif",
            google="Anton")                          # static: heavier than
                                                       # Archivo Black, no taper
UNBOUNDED = Face(stack=f"'Unbounded',{_SYSTEM}",
                 google="Unbounded:wght@200..900", wght=(200, 900))
FRAUNCES_NARROW = Face(
    stack="'Fraunces',Georgia,'Times New Roman',serif",
    google="Fraunces:opsz,wght,SOFT,WONK@9..144,400..900,0,1",
    wght=(400, 900), opsz=(9, 144))                   # the same family, the
                                                       # wonky/soft axes give a
                                                       # second, warmer voice


@dataclass(frozen=True)
class TypefacePair:
    """A display/body pair, and the structural type-system values they were
    tuned together for. §5 asks for a pair BY NAME from a curated table, not
    two independent face choices — a display face and a body face have to
    agree on measure, tracking and weight or the page reads as two different
    systems glued together, which is exactly what choosing them separately
    would risk.
    """

    display: Face
    body: Face
    modular_ratio: float
    display_steps: int
    tracking: float
    display_weight: int
    heading_weight: int
    voice: str          # one clause, what this pair reads as


# Roughly twenty families, paired. The six each mood already defaulted to are
# named here too (`fraunces-karla`, `sora-manrope`, `archivo-space-grotesk`,
# `playfair-jost`, `oswald-barlow`, `cormorant-karla`) so nothing regresses —
# a business that got one of them before still can, now by an explicit name
# rather than by mood alone, and a business whose mood and preferred voice
# used to be locked together can now ask for either independently.
TYPEFACE_PAIRS: dict[str, TypefacePair] = {
    "fraunces-karla": TypefacePair(
        FRAUNCES, KARLA, 1.28, 6, -0.012, 700, 600,
        "rustic, a warm serif over a plain grotesque"),
    "sora-manrope": TypefacePair(
        SORA, MANROPE, 1.2, 8, -0.022, 700, 600,
        "modern and calm, flat and quiet"),
    "archivo-space-grotesk": TypefacePair(
        ARCHIVO_BLACK, SPACE_GROTESK, 1.333, 6, -0.028, 400, 400,
        "loud, one heavy grotesque over a technical one"),
    "playfair-jost": TypefacePair(
        PLAYFAIR, JOST, 1.333, 6, 0.0, 600, 500,
        "high-contrast editorial serif over a geometric sans"),
    "oswald-barlow": TypefacePair(
        OSWALD, BARLOW, 1.25, 7, -0.02, 600, 500,
        "condensed and structural, a trade-shop wordmark"),
    "cormorant-karla": TypefacePair(
        CORMORANT, KARLA, 1.28, 7, 0.006, 600, 500,
        "quiet and airy serif, set slightly open"),
    "libre-caslon-work-sans": TypefacePair(
        LIBRE_CASLON, WORK_SANS, 1.25, 6, -0.006, 400, 500,
        "a book serif over a wide-range humanist sans — a firm rather than a "
        "brand"),
    "dm-serif-dm-sans": TypefacePair(
        DM_SERIF, DM_SANS, 1.28, 6, -0.01, 400, 500,
        "narrow high-contrast serif over its own sans sibling — one family, "
        "two registers"),
    "bodoni-inter": TypefacePair(
        BODONI, INTER, 1.333, 7, -0.008, 600, 600,
        "fashion-plate display serif over the most neutral sans available"),
    "ibm-plex-serif-inter": TypefacePair(
        IBM_PLEX_SERIF, INTER, 1.2, 6, -0.01, 600, 500,
        "an engineering firm's serif — designed, not decorative"),
    "lora-work-sans": TypefacePair(
        LORA, WORK_SANS, 1.22, 6, -0.008, 600, 500,
        "a calligraphic, readable serif over a wide humanist sans"),
    "league-spartan-dm-sans": TypefacePair(
        LEAGUE_SPARTAN, DM_SANS, 1.3, 7, -0.018, 700, 600,
        "geometric and confident, a studio rather than a shop"),
    "bebas-inter": TypefacePair(
        BEBAS_NEUE, INTER, 1.35, 6, 0.01, 400, 600,
        "tall condensed display over a quiet sans — a stadium marquee"),
    "anton-work-sans": TypefacePair(
        ANTON, WORK_SANS, 1.35, 6, -0.01, 400, 600,
        "the heaviest, most compressed display available — impossible to "
        "miss scrolling past"),
    "unbounded-manrope": TypefacePair(
        UNBOUNDED, MANROPE, 1.3, 7, -0.01, 600, 600,
        "rounded, geometric, a little playful without losing seriousness"),
    "fraunces-narrow-jost": TypefacePair(
        FRAUNCES_NARROW, JOST, 1.28, 6, -0.005, 500, 500,
        "the wonky, softer cut of a warm serif over a geometric sans"),
    "playfair-inter": TypefacePair(
        PLAYFAIR, INTER, 1.3, 6, -0.004, 700, 600,
        "editorial serif over the safest possible body face — chosen when "
        "the room is refined but the operator wants nothing to draw a "
        "complaint"),
    "oswald-inter": TypefacePair(
        OSWALD, INTER, 1.22, 6, -0.014, 600, 500,
        "condensed display kept quieter than the trade-shop pairing, for a "
        "trade that still wants to read as calm"),
    "sora-work-sans": TypefacePair(
        SORA, WORK_SANS, 1.18, 8, -0.018, 600, 500,
        "flat and quiet, a slightly warmer body face than the default"),
    "cormorant-jost": TypefacePair(
        CORMORANT, JOST, 1.3, 7, 0.002, 500, 500,
        "quiet serif over a geometric sans rather than a humanist one — "
        "cooler, more architectural"),
}

TYPEFACE_NAMES = tuple(sorted(TYPEFACE_PAIRS))


THEMES: dict[str, Theme] = {
    # Rustic: hairline rules and a warm ground. Fraunces has a real optical
    # axis, so its display cut is genuinely different from its text cut.
    "warm": Theme(
        bg="#fbf7f1", surface="#ffffff", raise_="#f4ece1", ink="#2a1f16",
        dim="#6f5c49", accent="#b4551f", accent_soft="#fbeade",
        accent_ink="#ffffff", line="#e9dcc9",
        display=FRAUNCES, body=KARLA,
        modular_ratio=1.28, display_steps=6, tracking=-0.012,
        display_weight=700, heading_weight=600,
        layout_bias="structured", radius="14px",
        hero_overlay=_scrim(38, 24, 14), grain=True),

    # Modern and calm: a flat scale and a lot of air, borders kept quiet.
    "fresh": Theme(
        bg="#f7fafb", surface="#ffffff", raise_="#eef4f6", ink="#0f1c24",
        dim="#4a606d", accent="#0d7f83", accent_soft="#e2f2f2",
        accent_ink="#ffffff", line="#dfeaee",
        display=SORA, body=MANROPE,
        modular_ratio=1.2, display_steps=8, tracking=-0.022,
        display_weight=700, heading_weight=600,
        layout_bias="airy", radius="16px",
        hero_overlay=_scrim(8, 24, 32)),

    # Loud: a grotesque that wants tight tracking and a compact measure.
    "bold": Theme(
        bg="#fffdf6", surface="#ffffff", raise_="#fdf3e0", ink="#171310",
        dim="#544c44", accent="#e04a1e", accent_soft="#ffe9df",
        accent_ink="#ffffff", line="#f0e4d2",
        display=ARCHIVO_BLACK, body=SPACE_GROTESK,
        modular_ratio=1.333, display_steps=6, tracking=-0.028,
        display_weight=400, heading_weight=400,      # the face has one weight
        layout_bias="contained", radius="6px",
        hero_overlay=_scrim(20, 14, 10)),

    # High-contrast serif: tracking at zero. Tightening Playfair at size closes
    # the apertures that carry its contrast.
    "refined": Theme(
        bg="#f7f5f2", surface="#ffffff", raise_="#efece6", ink="#17181a",
        dim="#585a55", accent="#1d5c46", accent_soft="#e5efea",
        accent_ink="#ffffff", line="#e3ded5",
        display=PLAYFAIR, body=JOST,
        modular_ratio=1.333, display_steps=6, tracking=0.0,
        display_weight=600, heading_weight=500,
        layout_bias="editorial", radius="3px",
        hero_overlay=_scrim(18, 18, 16), grain=True),

    # Condensed and structural: square corners, visible rules.
    "industrial": Theme(
        bg="#f2f2ef", surface="#ffffff", raise_="#e8e8e4", ink="#16181a",
        dim="#4f5459", accent="#b8410c", accent_soft="#fbe6dc",
        accent_ink="#ffffff", line="#dcdcd6",
        display=OSWALD, body=BARLOW,
        modular_ratio=1.25, display_steps=7, tracking=-0.02,
        display_weight=600, heading_weight=500,
        layout_bias="structured", radius="0px",
        hero_overlay=_scrim(20, 22, 24, 0.88)),

    # Dark and quiet: Cormorant is lighter and airier than it looks, so it is
    # set slightly OPEN — negative tracking would collapse it.
    "night": Theme(
        bg="#0f1115", surface="#171a20", raise_="#1d2129", ink="#f4f1ec",
        dim="#a7a49d", accent="#d9a441", accent_soft="#2a2418",
        accent_ink="#14151a", line="#2a2e37",
        display=CORMORANT, body=KARLA,
        modular_ratio=1.28, display_steps=7, tracking=0.006,
        display_weight=600, heading_weight=500,
        layout_bias="editorial", radius="8px",
        hero_overlay=_scrim(6, 7, 10, 0.90), grain=True),
}


# Which typeface pair a mood defaults to when nothing more specific was
# chosen — a replayed direction from before this axis existed, or the
# keyless fallback, which does not make a typeface call at all yet. Matches
# what `THEMES` already carries per mood, so applying it is a no-op for
# anything that was never asked to differ.
DEFAULT_TYPEFACE: dict[str, str] = {
    "warm": "fraunces-karla",
    "fresh": "sora-manrope",
    "bold": "archivo-space-grotesk",
    "refined": "playfair-jost",
    "industrial": "oswald-barlow",
    "night": "cormorant-karla",
}


def theme_for(mood: str, accent: str | None = None,
             typeface: str | None = None) -> Theme:
    """The theme for one mood, optionally recoloured and re-set in a named
    typeface pair. `typeface=None` keeps the mood's own default pairing —
    every existing call site that does not know about this axis yet keeps
    rendering exactly as it did before it existed.
    """
    base = THEMES.get(mood, THEMES["fresh"]).recoloured(accent)
    if typeface:
        return base.with_typeface(typeface)
    return base
