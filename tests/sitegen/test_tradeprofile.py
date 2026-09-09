"""BRIEF §5: which sections matter per trade, in what order, and what it's
called — one table per `trade_kind` rather than the two ad hoc conditions
(`_offer_heading`'s food-word match, `_CTA_BY_TRADE`'s own earlier copy) this
replaces.
"""

from __future__ import annotations

import pytest

from app.site import tradeprofile as tp

pytestmark = pytest.mark.unit

_KINDS = ("food", "care", "groom", "body", "desk", "trade", "retail")


def test_every_trade_kind_has_its_own_heading():
    """A heading table with one entry is a default with extra steps."""
    headings = {kind: tp.heading_for(kind, has_services=True, has_products=False)
                for kind in _KINDS}
    assert len(set(headings.values())) >= len(_KINDS) - 1, headings


def test_an_unrecognised_trade_falls_back_to_the_generic_heading():
    assert tp.heading_for("nonsense", True, False) == tp.HEADING["default"]


def test_products_with_no_services_is_a_shop_regardless_of_trade():
    """The shape of the material, not the trade word — a hardware counter
    with no listed services reads the same way a boutique does."""
    for kind in (*_KINDS, "default", "nonsense"):
        assert tp.heading_for(kind, has_services=False,
                              has_products=True) == tp.PRODUCTS_ONLY_HEADING


def test_the_products_only_rule_does_not_apply_when_services_exist_too():
    assert tp.heading_for("trade", has_services=True,
                          has_products=True) != tp.PRODUCTS_ONLY_HEADING


def test_default_emphasis_differs_by_trade():
    """The whole point of a per-trade default — if every trade got the same
    fallback order, the table would be one entry with extra names on it."""
    values = {kind: tp.emphasis_for(kind) for kind in _KINDS}
    assert len(set(values.values())) > 1, values
    for kind, order in values.items():
        assert order, f"{kind} has no default emphasis at all"


def test_an_unrecognised_trade_gets_no_default_emphasis():
    """No opinion is the honest answer for a trade this table has never
    seen — asserting one would be a guess wearing the same shape as a rule."""
    assert tp.emphasis_for("nonsense") == ()


def test_cta_words_still_works_from_its_new_home():
    """Moved from `render.py`, not rewritten — the existing behaviour and its
    existing tests (`tests/sitegen/test_hero.py`) must survive the move."""
    assert tp.cta_words("book", "food") == "Book a table"
    assert tp.cta_words("book", "default") == "Book now"
    assert tp.cta_words("nonsense", "default") == "Call us"


def test_only_trade_is_hunted_for_contractor_facts_today():
    """Widening this to another `trade_kind` is a real decision about that
    trade's own material, not a default to slide open by accident."""
    for kind in _KINDS:
        if kind == "trade":
            assert tp.facts_for(kind), "trade should hunt for something"
        else:
            assert tp.facts_for(kind) == (), (
                f"{kind} is hunted for contractor facts and should not be — "
                f"widening this is a decision, not a default")
