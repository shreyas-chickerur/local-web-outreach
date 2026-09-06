"""The plan must describe the page that gets built.

`plan.py`'s docstring says the plan exists so decisions can be corrected before
they become a page. That guarantee is only worth anything if the two agree, and
they did not: `plan_for` chose the hero before building the sections, and
`build_from_spec` chose it after — so the hero had already been handed out to
the gallery, and the workspace showed a four-tile plan beside a six-tile page.

Plan-versus-render divergence is a class of bug rather than one bug, which is
why this file tests the agreement itself and not just the hero.
"""

from __future__ import annotations

import re

import pytest

import app.site.render as render
from app.site.render import build_from_spec, plan_for
from app.site.spec import SiteSpec

pytestmark = pytest.mark.unit

# Six photographs, deliberately different shapes, so the choice is not
# arbitrary: /3 is the one a person would pick.
SIZES = {
    "https://x/1.jpg": (900, 700),
    "https://x/2.jpg": (1600, 1500),
    "https://x/3.jpg": (3200, 1800),
    "https://x/4.jpg": (2400, 1350),
    "https://x/5.jpg": (1200, 1600),
    "https://x/6.jpg": (2000, 1200),
}


@pytest.fixture
def measured(monkeypatch):
    monkeypatch.setattr(render, "measure", lambda url: SIZES.get(url))
    return SIZES


def _brief() -> dict:
    return {
        "name": "The Heritage Table",
        "facts": [{"field": "address", "value": "7110 Main St, Frisco, TX",
                   "confidence": "verified"},
                  {"field": "phone", "value": "(469) 664-0100",
                   "confidence": "verified"}],
        "published": {
            "tagline": "A neighbourhood restaurant on Main Street.",
            "about": "Scratch kitchen serving dinner nightly.",
            "services": ["Dinner Service", "Online Ordering"],
            "hours": ["Mon-Sat 5pm-9pm"], "menu_items": [], "menu_media": [],
            "photos": list(SIZES), "socials": [], "emails": [],
            "has_locations_page": False, "blocks": [], "products": [],
        },
        "ratings": [{"source": "google", "value": 4.6, "reviews": 676}],
    }


def page_images(html: str) -> list[str]:
    """Every photograph the page renders as an <img>, in order."""
    return re.findall(r'<img[^>]+src="([^"?]+)"', html)


def hero_background(html: str) -> str | None:
    found = re.search(r'class="bgimg" style="background-image:url\(&quot;([^&?]+)',
                      html)
    return found.group(1) if found else None


def test_the_hero_is_not_also_a_gallery_tile(measured):
    """It was, on every site ever generated. The audit never caught it because
    `check_images` compares <img> sources and the hero is a CSS background."""
    spec = SiteSpec()
    html = build_from_spec(_brief(), spec)
    hero = hero_background(html)
    assert hero, "no hero rendered"
    assert hero not in page_images(html)


def test_the_plan_and_the_page_choose_the_same_hero(measured):
    spec = SiteSpec()
    plan = plan_for(_brief(), spec)
    html = build_from_spec(_brief(), spec)
    assert plan.hero_photo == hero_background(html)


def test_the_plan_and_the_page_place_the_same_photographs(measured):
    """The general form. Two orderings of the same shared pool produce two
    different pages, and only one of them is on screen."""
    spec = SiteSpec()
    plan = plan_for(_brief(), spec)
    html = build_from_spec(_brief(), spec)

    planned = [url for section in plan.sections for url in section.images]
    rendered = page_images(html)
    assert planned == rendered, (
        f"the plan says {len(planned)} photographs, the page renders "
        f"{len(rendered)}")


def test_the_plan_and_the_page_agree_on_the_gallery_tile_count(measured):
    """The symptom as the operator saw it: a plan promising four tiles in two
    columns beside a page rendering six in three."""
    spec = SiteSpec()
    plan = plan_for(_brief(), spec)
    html = build_from_spec(_brief(), spec)
    gallery = next((s for s in plan.sections if s.key == "gallery"), None)
    assert gallery is not None
    inside = re.search(r'<section id="gallery".*?</section>', html, re.S)
    assert inside
    assert len(gallery.images) == len(page_images(inside.group(0)))


def test_they_still_agree_when_measurement_is_unavailable(monkeypatch):
    """Agreement must not depend on the thing that was broken. With no sizes at
    all the two must still make the same choice as each other."""
    monkeypatch.setattr(render, "measure", lambda url: None)
    spec = SiteSpec()
    plan = plan_for(_brief(), spec)
    html = build_from_spec(_brief(), spec)
    assert plan.hero_photo == hero_background(html)
    assert hero_background(html) not in page_images(html)
