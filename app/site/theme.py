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

from dataclasses import dataclass
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
INTER = Face(stack=f"'Inter',{_SYSTEM}", google="Inter:opsz,wght@14..32,100..900",
             wght=(100, 900), opsz=(14, 32))

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


THEMES: dict[str, Theme] = {
    # Rustic: hairline rules and a warm ground. Fraunces has a real optical
    # axis, so its display cut is genuinely different from its text cut.
    "warm": Theme(
        bg="#fbf7f1", surface="#ffffff", raise_="#f4ece1", ink="#2a1f16",
        dim="#6f5c49", accent="#b4551f", accent_soft="#fbeade",
        accent_ink="#ffffff", line="#e9dcc9",
        display=FRAUNCES, body=INTER,
        modular_ratio=1.28, display_steps=6, tracking=-0.012,
        display_weight=700, heading_weight=600,
        layout_bias="structured", radius="14px",
        hero_overlay=_scrim(38, 24, 14), grain=True),

    # Modern and calm: a flat scale and a lot of air, borders kept quiet.
    "fresh": Theme(
        bg="#f7fafb", surface="#ffffff", raise_="#eef4f6", ink="#0f1c24",
        dim="#4a606d", accent="#0d7f83", accent_soft="#e2f2f2",
        accent_ink="#ffffff", line="#dfeaee",
        display=SORA, body=INTER,
        modular_ratio=1.2, display_steps=8, tracking=-0.022,
        display_weight=700, heading_weight=600,
        layout_bias="airy", radius="16px",
        hero_overlay=_scrim(8, 24, 32)),

    # Loud: a grotesque that wants tight tracking and a compact measure.
    "bold": Theme(
        bg="#fffdf6", surface="#ffffff", raise_="#fdf3e0", ink="#171310",
        dim="#544c44", accent="#e04a1e", accent_soft="#ffe9df",
        accent_ink="#ffffff", line="#f0e4d2",
        display=ARCHIVO_BLACK, body=INTER,
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
        display=PLAYFAIR, body=INTER,
        modular_ratio=1.333, display_steps=6, tracking=0.0,
        display_weight=600, heading_weight=500,
        layout_bias="editorial", radius="3px",
        hero_overlay=_scrim(18, 18, 16), grain=True),

    # Condensed and structural: square corners, visible rules.
    "industrial": Theme(
        bg="#f2f2ef", surface="#ffffff", raise_="#e8e8e4", ink="#16181a",
        dim="#4f5459", accent="#b8410c", accent_soft="#fbe6dc",
        accent_ink="#ffffff", line="#dcdcd6",
        display=OSWALD, body=INTER,
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
        display=CORMORANT, body=INTER,
        modular_ratio=1.28, display_steps=7, tracking=0.006,
        display_weight=600, heading_weight=500,
        layout_bias="editorial", radius="8px",
        hero_overlay=_scrim(6, 7, 10, 0.90), grain=True),
}


def theme_for(mood: str) -> Theme:
    return THEMES.get(mood, THEMES["fresh"])
