"""The detail pass: the things that separate a designed page from a rendered one.

Each of these is invisible when it works and unmissable when it does not, which
is exactly the kind of thing that rots silently.
"""

from __future__ import annotations

import re

import pytest

from app.site.render import build
from app.site.theme import THEMES, rgb, rgba

pytestmark = pytest.mark.unit

BRIEF = {"name": "Test Co", "facts": [],
         "published": {"services": ["A", "B", "C", "D"], "products": [],
                       "menu_items": [], "hours": [], "photos": [],
                       "socials": [], "emails": [], "tagline": "Hello"},
         "ratings": []}


def page(mood: str = "") -> str:
    return build(BRIEF, mood)[0]


# ------------------------------------------------------- translucent nav -- #
def test_the_sticky_nav_is_translucent_not_solid():
    """A solid bar is the tell. The page reading through it is the cue."""
    markup = page("warm")
    stuck = re.search(r"\.bar\.stuck\{([^}]*)\}", markup).group(1)
    assert "backdrop-filter:blur(" in stuck
    assert "-webkit-backdrop-filter" in stuck        # Safari still needs it
    assert re.search(r"background:rgba\([\d,]+,0\.\d+\)", stuck)
    assert "border-bottom:1px solid rgba(" in stuck


def test_the_nav_falls_back_opaque_without_blur_support():
    """Translucency with no blur behind it reads as a bug, not a style."""
    markup = page("warm")
    assert "@supports not ((backdrop-filter" in markup
    fallback = markup[markup.index("@supports not (("):]
    assert "background:var(--surface)" in fallback[:260]


def test_the_nav_tint_comes_from_the_theme_not_a_hard_coded_white():
    """A nav tinted white works on five themes and looks broken on the dark
    one."""
    light = re.search(r"\.bar\.stuck\{[^}]*background:(rgba\([^)]*\))",
                      page("warm")).group(1)
    dark = re.search(r"\.bar\.stuck\{[^}]*background:(rgba\([^)]*\))",
                     page("dark moody bar")).group(1)
    assert light != dark
    assert rgb(THEMES["night"].surface)[0] == int(dark.split("(")[1].split(",")[0])


# ------------------------------------------------------------- typography - #
def test_headings_balance_so_they_do_not_orphan_a_word():
    markup = page()
    heading_rule = re.search(r"h1,h2,h3\{([^}]*)\}", markup).group(1)
    assert "text-wrap:balance" in heading_rule


def test_the_hero_line_and_body_copy_are_wrapped_deliberately():
    markup = page()
    assert ".hero .sub,.lede,.eyebrow{text-wrap:balance}" in markup
    assert "p{text-wrap:pretty}" in markup


# ------------------------------------------------------------- interaction - #
def test_focus_is_visible_and_in_the_theme_accent():
    markup = page()
    rule = re.search(r":focus-visible\{([^}]*)\}", markup).group(1)
    assert "outline:2px solid var(--accent)" in rule
    assert "outline-offset" in rule


def test_a_mouse_click_does_not_leave_a_ring_behind():
    """Focus rings are for keyboards; showing them on click is the reason
    people used to remove them altogether."""
    assert ":focus:not(:focus-visible){outline:none}" in page()


@pytest.mark.parametrize("mood", list(THEMES))
def test_selected_text_takes_the_brand_colour(mood):
    markup = build(BRIEF, mood)[0]
    selection = re.search(r"::selection\{([^}]*)\}", markup).group(1)
    accent = rgba(THEMES[mood].accent, 0.24)
    assert accent in selection


# ---------------------------------------------------------- fine detail --- #
def test_shadows_are_two_layers_not_one_heavy_one():
    """A single heavy shadow reads as a border with a blur on it."""
    markup = page()
    shadow = re.search(r"--shadow:([^;]*);", markup).group(1)
    assert shadow.count("rgba(") == 2
    assert "8px 30px" in shadow          # the wide, faint cast


def test_a_section_boundary_is_drawn_rather_than_implied():
    markup = page()
    assert "section+section::before{content:" in markup
    assert "height:1px" in markup


@pytest.mark.parametrize("mood,expected", [
    ("clean modern minimal", "linear-gradient(90deg,transparent"),   # airy: fades out
    ("warm and rustic", "background:var(--line)"),                   # structured: solid
    ("bold and punchy", "height:2px"),                               # contained: heavier
    ("elegant upscale", "left:clamp("),                              # editorial: inset
])
def test_each_bias_draws_its_own_divider(mood, expected):
    markup = build(BRIEF, mood)[0]
    # From the body tag, not the first match in the document — the stylesheet
    # mentions every bias, so an unscoped search always returns the first one.
    bias = re.search(r'<body[^>]*data-theme-layout="(\w+)"', markup).group(1)
    rule = re.search(
        r'\[data-theme-layout="' + bias + r'"\] section\+section::before\{([^}]*)\}',
        markup).group(1)
    assert expected in rule


def test_cards_carry_a_micro_gradient_not_a_flat_fill():
    markup = page()
    card = re.search(r"\n\.card\{([^}]*)\}", markup).group(1)
    assert "linear-gradient(180deg" in card


def test_colour_maths_is_exact():
    assert rgb("#ffffff") == (255, 255, 255)
    assert rgb("#fff") == (255, 255, 255)
    assert rgba("#0d7f83", 0.5) == "rgba(13,127,131,0.5)"


def test_the_density_fallback_is_defined_on_the_root():
    """The hero is a <header>, not a <section>. Scoping --density-scale to
    sections left it undefined there, which makes
    calc(clamp(...) * var(--density-scale)) invalid at computed-value time —
    and the headline silently collapsed to the inherited body size."""
    markup = page("warm")
    root = re.search(r":root\{([^}]*)\}", markup).group(1)
    assert "--density-scale:1" in root


def test_every_size_that_uses_the_density_variable_can_resolve_outside_a_section():
    """Any rule multiplying by --density-scale must have a value to multiply by
    wherever it applies, or the declaration is dropped entirely."""
    markup = page("warm")
    users = re.findall(r"([a-z0-9 .#\[\]=\"-]+)\{[^}]*var\(--density-scale\)", markup)
    assert users, "nothing uses the variable — the test is watching the wrong thing"
    root = re.search(r":root\{([^}]*)\}", markup).group(1)
    assert "--density-scale" in root      # inherited by every one of them


def test_a_counted_number_is_guaranteed_to_land():
    """requestAnimationFrame stops in a throttled or backgrounded tab, leaving
    the number frozen part-way — a visitor reading "674 reviews" for a business
    that has 676. Timers keep running, so the real figure has to be forced."""
    markup = page("warm")
    assert "setTimeout(settle" in markup
    assert 'addEventListener("visibilitychange", settle' in markup


def test_the_page_is_readable_without_javascript():
    """Hiding content by default and revealing it with a script meant a
    sandboxed preview — and any crawler, and anyone with scripting off — saw
    the hero and nothing else at all."""
    markup = page("warm")
    # The reveal styles are scoped to a class only a script can add.
    assert "html.reveals [data-reveal]{opacity:0" in markup
    assert "[data-reveal]{opacity:0" not in markup.replace(
        "html.reveals [data-reveal]{opacity:0", "")
    # And that script runs in the head, before anything paints.
    head = markup[:markup.index("</head>")]
    assert "className+=' reveals'" in head


def test_clip_path_reveals_are_gated_the_same_way():
    """A picture masked to a sliver is the same failure as invisible text."""
    markup = page("warm")
    assert "html.reveals .mosaic img{clip-path:inset(" in markup
    assert "html.reveals .editorial-art img{clip-path:inset(" in markup
