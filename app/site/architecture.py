"""How the sections are arranged and spaced relative to each other.

Axis three, and it is here because the instrument said so rather than because
`BRIEF` §2.1 lists it fourth. After the type-setting rule landed, **all sixteen
live verdicts were exactly "do they share `first_screen`"** — with colour,
subject and type setting discounted by the judging rules, the generator had one
arrangement dimension, so a blind verdict had nothing else to rest on. Labels
that restate one axis measure self-consistency, not validity. This is the second
arrangement dimension.

Not `section_order` and not `compositions`. Those are mostly downstream of what
the business happens to publish — a restaurant with a menu and one without are
not two studios at work — which is why they carry 0.5 decidedness. This is the
part somebody chooses: how the bands sit against each other, independent of
which bands exist.

    STACKED   generous even rhythm, one ground, a hairline between sections.
              What every page does now, named so it stops being the absence of
              a decision.
    BANDED    the ground alternates on every section, hard-edged, no rules.
              The page reads as a stack of slabs.
    LEDGER    tight rhythm, a ruled line above every section, a narrow measure.
              Reads as a printed document — trades, law, dental.
    COLUMN    the content held in a narrow column against a wide empty margin,
              which is the arrangement a margin note lives in.
    GALLERY   a wide measure and a lot of air, for a business whose pictures
              are the argument.

Nothing here decides WHICH arrangement; the identity call does. This module owns
what each one means and what a business's material can carry.
"""

from __future__ import annotations

import re

from app.site.render import Material

# Ordered. The fingerprint compares positionally and the census prints them.
ARRANGEMENTS: tuple[str, ...] = ("stacked", "banded", "ledger", "column",
                                 "gallery")

DEFAULT = "stacked"

# An arrangement is a relationship BETWEEN sections, so it needs sections to
# hold a relationship between. Below these counts the page has nothing to
# arrange and every value renders the same thing — which is the `photo`/`facts`
# defect, and the reason availability is a real constraint here rather than a
# formality.
NEEDS_SECTIONS = {"stacked": 0, "banded": 3, "ledger": 2, "column": 3,
                  "gallery": 2}


def available(m: Material, sections: int) -> list[str]:
    """The arrangements this business's material can carry.

    `gallery` additionally needs photographs: a wide measure and a lot of air
    around nothing is not an arrangement, it is an empty page.
    """
    can = [name for name in ARRANGEMENTS if sections >= NEEDS_SECTIONS[name]]
    if not m.images:
        can = [name for name in can if name != "gallery"]
    return can


def arrange(body: str, arrangement: str) -> str:
    """Apply the arrangement to the assembled sections.

    Rewrites attributes on the section tags rather than adding a class to the
    body, deliberately. A body class is a hook, and a hook is exactly what
    `photo` and `facts` differed by — the page has to differ in what it says,
    not only in what it is called, or the standing test cannot tell a real
    arrangement from a named one.
    """
    if arrangement == "banded":
        # The ground alternates whatever each builder asked for. One place
        # decides the ground, which is the rule the section CSS already keeps.
        count = {"n": 0}

        def flip(match: re.Match[str]) -> str:
            tag = re.sub(r'\s+data-ground="[^"]*"', "", match.group(0))
            ground = "raise" if count["n"] % 2 else "base"
            count["n"] += 1
            return f'{tag[:-1]} data-ground="{ground}">'

        return re.sub(r"<section\b[^>]*>", flip, body)
    if arrangement == "ledger":
        return re.sub(r"<section\b", '<section data-rule="on"', body).replace(
            '<div class="wrap">', '<div class="wrap" data-measure="tight">')
    if arrangement == "column":
        return body.replace('<div class="wrap">',
                            '<div class="wrap" data-measure="column">')
    if arrangement == "gallery":
        return body.replace('<div class="wrap">',
                            '<div class="wrap" data-measure="wide">')
    return body
