"""The forbidden defaults, encoded and checked. `BRIEF` §2.4.

The list is not advice. A site matching one of these is a defect on the same
footing as a contrast failure, and §2.4 says so — but it had only ever been
prose, which is this project's recurring defect written into the brief itself.
These are mechanical, they run over the rendered page and the resolved theme,
and the census reports how many fixtures trip them.

§2.4 also says the six existing moods sit close to several of these. That is
expected to show up as failures rather than as a clean sheet: they are fallbacks
to escape, not the target, and a check that passed everything on the first run
would mean the check was written to pass.
"""

from __future__ import annotations

import re

# Roughly, the hues §2.4 names. Kept as ranges rather than exact strings
# because a palette is sampled and repaired, so an exact match would miss by
# one step and report a clean sheet.
_ACID = ("lime", "acid", "chartreuse", "vermilion")
_SAFE_FACES = ("Inter", "Space Grotesk")
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF☀-➿️]")


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def check(page: str, theme, spec) -> list[str]:
    """Which forbidden defaults this page matches. Empty is the target."""
    found: list[str] = []
    display = getattr(getattr(theme, "display", None), "stack", "") or ""
    body = getattr(getattr(theme, "body", None), "stack", "") or ""
    accent = str(getattr(spec, "accent", "") or "")
    mood = str(getattr(spec, "mood", "") or "")

    # 1. warm cream with a serif display and a terracotta accent
    if (mood == "warm" and "serif" in display.lower()
            and accent in ("terracotta", "rust", "clay")):
        found.append("warm cream + serif display + terracotta")

    # 2. near-black with one acid accent
    ground = getattr(theme, "bg", "") or ""
    if ground.startswith("#"):
        try:
            r, g, b = _hex_to_rgb(ground)
            if r + g + b < 150 and any(w in accent.lower() for w in _ACID):
                found.append("near-black + one acid accent")
        except ValueError:
            pass

    # 3. a purple-to-blue gradient hero
    hero = page[page.find("<header"):page.find("</header>")]
    if "gradient" in hero and re.search(r"purple|violet|indigo|#[46-9a-f]", hero):
        if "gradient" in hero and "blue" in hero:
            found.append("purple-to-blue gradient hero")

    # 4. the safe face
    for face in _SAFE_FACES:
        if face in display or face in body:
            found.append(f"{face} as the safe face")

    # 5. one radius and one shadow everywhere
    radii = set(re.findall(r"border-radius:\s*([0-9.]+px)", page))
    shadows = set(re.findall(r"box-shadow:\s*([^;}]+)", page))
    if len(radii) == 1 and len(shadows) == 1:
        found.append("uniform radius and shadow on everything")

    # 6. an accent rail on rounded cards, repeated
    if re.search(r"\.card\{[^}]*border-left:[^;]*var\(--accent\)", page) and radii:
        found.append("accent rail on rounded cards")

    # 7. emoji as section markers
    headings = re.findall(r"<h2[^>]*>(.*?)</h2>", page, re.S)
    if any(_EMOJI.search(h) for h in headings):
        found.append("emoji as section markers")

    # 8. everything centred
    centred = len(re.findall(r"text-align:\s*center", page))
    if centred >= 6:
        found.append("everything centred")

    # 9. a full-viewport hero that pushes the page out of the first screen
    if re.search(r"\.hero[^{]*\{[^}]*min-height:\s*(100vh|min\(100vh)", page):
        found.append("full-viewport hero")
    return found
