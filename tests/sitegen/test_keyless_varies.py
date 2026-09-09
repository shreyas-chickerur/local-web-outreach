"""`BRIEF` §2.6: the degraded path still has to vary by business.

`fallback_opening` mapped a business purely by trade keyword, so two roofers on
the same street got byte-identical sites — the exact failure §2 exists to
prevent, arriving through the door marked "no key". Everything degrades without
a key, and the degraded path is still something the operator sells.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site import fingerprint as fp
from app.site.opening import fallback_opening
from app.site.pipeline import spec_from_config
from app.site.render import material_from_brief, plan_for

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")
DECIDED = ("mood", "accent", "first_screen", "type_treatment", "architecture",
           "signature")


def brief_named(slug: str, name: str) -> dict:
    payload = json.loads((FIXTURES / f"{slug}.json").read_text())
    payload.pop("design_direction", None)
    return {**payload, "name": name, "lead_id": 1}


def test_two_businesses_in_one_trade_do_not_collide_without_a_key():
    one = fallback_opening(brief_named("roofer", "Status Roofing LLC"))
    two = fallback_opening(brief_named("roofer", "Lone Star Roofing Co"))
    assert one["mood"] == two["mood"], (
        "the trade should still choose the mood — it is the one thing a trade "
        "genuinely implies")
    moved = [key for key in DECIDED if one.get(key) != two.get(key)]
    assert len(moved) >= 3, (
        f"two roofers with different names differ on only {moved} without a "
        f"key. §2.6: deterministic, but not identical.")


def test_the_keyless_answer_is_the_same_every_time():
    """Deterministic, or the replay invariant is gone: a rebuild would produce
    a different site from the same brief."""
    brief = brief_named("salon", "Somewhere Salon")
    first = fallback_opening(brief)
    for _ in range(3):
        assert fallback_opening(brief) == first


def test_the_keyless_answer_only_offers_what_the_business_can_carry():
    """The same constraint the model gets. A position or a device the material
    cannot support is a broken page, whoever chose it."""
    from app.site.opening import (
        available_arrangements,
        available_devices,
        available_positions,
        available_treatments,
    )

    for slug in ("threadbare", "restaurant-bare", "hvac"):
        brief = brief_named(slug, json.loads(
            (FIXTURES / f"{slug}.json").read_text())["name"])
        config = fallback_opening(brief)
        assert config["first_screen"] in available_positions(brief)
        assert config["type_treatment"] in available_treatments(brief)
        assert config["architecture"] in available_arrangements(brief)
        assert config["signature"] in available_devices(brief)


def test_the_keyless_path_renders_a_real_page():
    """It has to survive the whole pipeline, not just produce a dict."""
    brief = brief_named("roofer", "Lone Star Roofing Co")
    spec = spec_from_config({k: v for k, v in fallback_opening(brief).items()
                             if k not in ("rationale", "read_by")})
    print_of = fp.of(plan_for(brief, spec), spec, material_from_brief(brief))
    assert print_of.values["first_screen"]
    assert print_of.values["signature"]
