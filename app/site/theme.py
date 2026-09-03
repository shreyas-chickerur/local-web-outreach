"""Palettes and type — one complete world per mood.

Each is a whole set rather than a hue swapped into a template: a warm palette
that keeps a cold link colour reads as a theme switcher, not a design. Every
one carries its own display face, its own accent and a second tone for depth,
so two moods produce sites that look like different studios made them.
"""

from __future__ import annotations

from dataclasses import dataclass


def _scrim(r: int, g: int, b: int, weight: float = 0.84) -> str:
    """A directional wash: heavy where the words sit, clear where the photo is.

    Businesses put their logo and their own lettering into their photographs,
    so a hero cannot assume a clean image.
    """
    return (f"linear-gradient(105deg,rgba({r},{g},{b},{weight}) 0%,"
            f"rgba({r},{g},{b},{weight - .30:.2f}) 42%,"
            f"rgba({r},{g},{b},{weight - .62:.2f}) 100%)")


@dataclass(frozen=True)
class Theme:
    bg: str
    surface: str
    raise_: str          # a second surface, for banding sections
    ink: str
    dim: str
    accent: str
    accent_soft: str     # tinted background of the accent
    accent_ink: str
    line: str
    display: str
    body: str
    fonts: str           # the Google Fonts href for this pairing
    radius: str
    hero_overlay: str
    grain: bool = False  # a faint noise layer, for the tactile moods


_BODY = ("'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
         "Helvetica,Arial,sans-serif")


def _href(*families: str) -> str:
    query = "&".join(f"family={f}" for f in families)
    return f"https://fonts.googleapis.com/css2?{query}&display=swap"


THEMES: dict[str, Theme] = {
    "warm": Theme(
        bg="#fbf7f1", surface="#ffffff", raise_="#f4ece1", ink="#2a1f16",
        dim="#6f5c49", accent="#b4551f", accent_soft="#fbeade",
        accent_ink="#ffffff", line="#e9dcc9",
        display="'Fraunces',Georgia,serif", body=_BODY,
        fonts=_href("Fraunces:opsz,wght@9..144,600;9..144,700",
                    "Inter:wght@400;500;600;700"),
        radius="14px", hero_overlay=_scrim(38, 24, 14), grain=True),
    "fresh": Theme(
        bg="#f7fafb", surface="#ffffff", raise_="#eef4f6", ink="#0f1c24",
        dim="#4a606d", accent="#0d7f83", accent_soft="#e2f2f2",
        accent_ink="#ffffff", line="#dfeaee",
        display="'Sora',-apple-system,sans-serif", body=_BODY,
        fonts=_href("Sora:wght@600;700;800", "Inter:wght@400;500;600;700"),
        radius="16px", hero_overlay=_scrim(8, 24, 32)),
    "bold": Theme(
        bg="#fffdf6", surface="#ffffff", raise_="#fdf3e0", ink="#171310",
        dim="#544c44", accent="#e04a1e", accent_soft="#ffe9df",
        accent_ink="#ffffff", line="#f0e4d2",
        display="'Archivo Black',Impact,sans-serif", body=_BODY,
        fonts=_href("Archivo+Black", "Inter:wght@400;500;600;700"),
        radius="6px", hero_overlay=_scrim(20, 14, 10)),
    "refined": Theme(
        bg="#f7f5f2", surface="#ffffff", raise_="#efece6", ink="#17181a",
        dim="#585a55", accent="#1d5c46", accent_soft="#e5efea",
        accent_ink="#ffffff", line="#e3ded5",
        display="'Playfair Display',Didot,Georgia,serif", body=_BODY,
        fonts=_href("Playfair+Display:wght@500;600;700",
                    "Inter:wght@400;500;600;700"),
        radius="3px", hero_overlay=_scrim(18, 18, 16), grain=True),
    "industrial": Theme(
        bg="#f2f2ef", surface="#ffffff", raise_="#e8e8e4", ink="#16181a",
        dim="#4f5459", accent="#b8410c", accent_soft="#fbe6dc",
        accent_ink="#ffffff", line="#dcdcd6",
        display="'Oswald',Impact,sans-serif", body=_BODY,
        fonts=_href("Oswald:wght@500;600;700", "Inter:wght@400;500;600;700"),
        radius="0px", hero_overlay=_scrim(20, 22, 24, 0.88)),
    "night": Theme(
        bg="#0f1115", surface="#171a20", raise_="#1d2129", ink="#f4f1ec",
        dim="#a7a49d", accent="#d9a441", accent_soft="#2a2418",
        accent_ink="#14151a", line="#2a2e37",
        display="'Cormorant Garamond',Georgia,serif", body=_BODY,
        fonts=_href("Cormorant+Garamond:wght@600;700",
                    "Inter:wght@400;500;600;700"),
        radius="8px", hero_overlay=_scrim(6, 7, 10, 0.90), grain=True),
}


def theme_for(mood: str) -> Theme:
    return THEMES.get(mood, THEMES["fresh"])
