"""A mood as structural decisions, not a palette with a font name.

What these pin: that six themes differ in more than colour, that tracking is
chosen per typeface rather than globally, and that the variable fonts we pay to
download are actually driven.
"""

from __future__ import annotations

import re

import pytest

from app.site.render import build
from app.site.theme import THEMES, Face, theme_for

pytestmark = pytest.mark.unit


def _page(mood: str) -> str:
    brief = {"name": "Test Co", "facts": [],
             "published": {"services": ["A", "B", "C", "D"], "products": [],
                           "menu_items": [], "hours": [], "photos": [],
                           "socials": [], "emails": [], "tagline": "Hello"},
             "ratings": []}
    return build(brief, mood)[0]


# ----------------------------------------------------------- optics ------ #
def test_high_contrast_serifs_are_not_tracked_tight():
    """Tightening Playfair or Cormorant at display size closes the apertures
    that carry their contrast. A global -0.025em did exactly that."""
    assert THEMES["refined"].tracking == 0.0            # Playfair Display
    assert THEMES["night"].tracking > 0                 # Cormorant, set open


def test_grotesques_keep_their_tight_tracking():
    assert THEMES["bold"].tracking <= -0.025            # Archivo Black
    assert THEMES["industrial"].tracking < 0            # Oswald


def test_tracking_eases_off_as_the_size_drops():
    """The figure that flatters a 96px headline is too tight at 22px."""
    theme = THEMES["bold"]
    h1 = float(theme.tracking_for(theme.display_steps).rstrip("em"))
    h3 = float(theme.tracking_for(2).rstrip("em"))
    assert h1 == pytest.approx(theme.tracking)
    assert h3 == 0.0
    assert abs(h1) > abs(h3)


@pytest.mark.parametrize("mood", list(THEMES))
def test_every_theme_states_its_tracking_per_level(mood):
    page = _page(mood)
    assert re.search(r"h1\{[^}]*letter-spacing:", page)
    assert re.search(r"h3\{[^}]*letter-spacing:", page)


# ------------------------------------------------------ variable axes ---- #
def test_a_variable_face_is_actually_driven():
    """Requesting opsz 9..144 and then never setting it is paying for a
    variable font and using it statically."""
    warm = _page("warm")                     # Fraunces: opsz + wght
    assert 'font-variation-settings:"opsz" 144' in warm
    assert '"wght"' in warm
    # and the optical size differs between levels, which is the whole point
    assert '"opsz" 36' in warm


def test_a_static_face_gets_weight_not_variation_settings():
    """Archivo Black has one weight. Writing font-variation-settings for it
    would override font-weight and buy nothing."""
    bold = _page("bold")
    heading = re.search(r"h1\{([^}]*)\}", bold).group(1)
    assert "font-variation-settings" not in heading
    assert "font-weight:400" in heading


def test_the_weight_axis_is_always_written_alongside_opsz():
    """font-variation-settings overrides font-weight, so omitting wght snaps
    the face back to 400."""
    face = Face(stack="x", wght=(100, 900), opsz=(9, 144))
    assert face.variation(700, 144) == '"opsz" 144,"wght" 700'


def test_axis_values_are_clamped_to_what_the_face_exposes():
    face = Face(stack="x", wght=(300, 700), opsz=(9, 48))
    assert face.variation(900, 144) == '"opsz" 48,"wght" 700'


def test_the_font_request_asks_for_the_ranges_it_drives():
    """A css2 URL pinned to single weights returns static instances, and the
    axes silently do nothing."""
    assert "9..144" in THEMES["warm"].fonts_href           # Fraunces opsz
    assert "400..900" in THEMES["warm"].fonts_href         # and its weights


# ---------------------------------------------------- modular scale ------ #
def test_sizes_come_off_one_scale_not_three_clamps():
    theme = THEMES["refined"]
    scale = theme.scale
    assert scale["h1"] != scale["h2"] != scale["h3"]
    # h1 sits display_steps above body, h3 two above: the ratio is systematic
    biggest = float(re.search(r"clamp\(([\d.]+)px", scale["h1"]).group(1))
    middle = float(re.search(r"clamp\(([\d.]+)px", scale["h2"]).group(1))
    smallest = float(re.search(r"clamp\(([\d.]+)px", scale["h3"]).group(1))
    assert biggest > middle > smallest


def test_a_flatter_ratio_produces_a_quieter_page():
    calm = THEMES["fresh"].modular_ratio          # 1.2
    editorial = THEMES["refined"].modular_ratio   # 1.333
    assert calm < editorial


def test_the_small_end_of_the_scale_is_damped():
    """A 1.333 ratio taken straight to a phone gives a 90px headline that will
    not fit. The narrow end uses a flatter ratio."""
    theme = THEMES["refined"]
    assert theme.small_ratio < theme.modular_ratio
    smallest = float(re.search(r"clamp\(([\d.]+)px", theme.scale["h1"]).group(1))
    assert smallest < 60


def test_headline_size_stays_inside_sane_bounds_for_every_theme():
    for mood, theme in THEMES.items():
        low, high = re.findall(r"([\d.]+)px", theme.scale["h1"])[0::2][:2]
        assert 34 <= float(low) <= 60, f"{mood} too big/small on a phone"


# --------------------------------------------------- layout intent ------- #
def test_each_theme_declares_a_structural_bias():
    biases = {t.layout_bias for t in THEMES.values()}
    assert len(biases) >= 3          # not all one bias with different paint


def test_the_bias_reaches_the_markup():
    page = _page("fresh")
    assert 'data-theme-layout="airy"' in page
    assert '[data-theme-layout="airy"] section{padding:' in page


def test_the_biases_differ_structurally_not_only_in_colour():
    airy, structured = _page("fresh"), _page("warm")
    assert 'data-theme-layout="airy"' in airy
    assert 'data-theme-layout="structured"' in structured
    # an airy theme drops its borders; a structured one draws rules
    assert '[data-theme-layout="airy"] .card' in airy
    assert 'section+section{border-top' in structured


def test_theme_lookup_falls_back_rather_than_raising():
    assert theme_for("nonsense") is THEMES["fresh"]
