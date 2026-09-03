"""Palettes and type, one per mood.

Six is enough to cover what a local business asks for, and each is a whole
coherent set rather than a hue swapped in a template: a warm palette that keeps
a cold link colour looks like a theme switcher, not a design.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    bg: str
    surface: str
    ink: str
    dim: str
    accent: str
    accent_ink: str      # text that sits on the accent
    line: str
    display: str         # heading face
    body: str
    radius: str
    hero_overlay: str


def _scrim(r: int, g: int, b: int, weight: float = 0.86) -> str:
    """A directional wash: heavy where the words sit, clear where the photo is.

    Businesses put their logo and their own lettering straight into the photos
    on their site, so a hero cannot assume a clean image. This keeps a headline
    readable over anything without hiding the picture.
    """
    return (f"linear-gradient(100deg,rgba({r},{g},{b},{weight}) 0%,"
            f"rgba({r},{g},{b},{weight - .26:.2f}) 46%,"
            f"rgba({r},{g},{b},{weight - .64:.2f}) 100%)")


_STACK = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"

THEMES: dict[str, Theme] = {
    "warm": Theme(
        bg="#faf6f0", surface="#ffffff", ink="#2b2018", dim="#6b5949",
        accent="#a2542b", accent_ink="#ffffff", line="#e8dccd",
        display="'Georgia','Iowan Old Style',serif", body=_STACK,
        radius="10px",
        hero_overlay=_scrim(38, 26, 18)),
    "fresh": Theme(
        bg="#f7f9fa", surface="#ffffff", ink="#16212b", dim="#516170",
        accent="#0e7c86", accent_ink="#ffffff", line="#e0e8ec",
        display=f"'Helvetica Neue',{_STACK}", body=_STACK,
        radius="12px",
        hero_overlay=_scrim(9, 22, 31)),
    "bold": Theme(
        bg="#fffdf7", surface="#ffffff", ink="#1a1a1a", dim="#565049",
        accent="#e2542c", accent_ink="#ffffff", line="#eee4d6",
        display=f"'Impact','Haettenschweiler',{_STACK}", body=_STACK,
        radius="4px", hero_overlay=_scrim(20, 18, 16)),
    "refined": Theme(
        bg="#f6f4f1", surface="#ffffff", ink="#1c1c1a", dim="#5d5a53",
        accent="#1f4d3d", accent_ink="#ffffff", line="#e4e0d8",
        display="'Didot','Bodoni MT',Georgia,serif", body=_STACK,
        radius="2px", hero_overlay=_scrim(22, 22, 20)),
    "industrial": Theme(
        bg="#f2f2f0", surface="#ffffff", ink="#1d1f21", dim="#565b60",
        accent="#c2410c", accent_ink="#ffffff", line="#dcdcd8",
        display=f"'Oswald','Arial Narrow',{_STACK}", body=_STACK,
        radius="0px", hero_overlay=_scrim(24, 26, 28, 0.88)),
    "night": Theme(
        bg="#14151a", surface="#1c1e25", ink="#f2f0ec", dim="#a9a49b",
        accent="#d4a24c", accent_ink="#14151a", line="#2b2e37",
        display="'Georgia',serif", body=_STACK,
        radius="6px", hero_overlay=_scrim(8, 9, 12, 0.9)),
}


def theme_for(mood: str) -> Theme:
    return THEMES.get(mood, THEMES["fresh"])
