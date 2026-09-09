"""BRIEF §5's contractor facts — the four this generator ships. Each is
found or it is not; nothing here is ever generated or inferred from the
trade, only matched against text the business actually published.
"""

from __future__ import annotations

import pytest

from app.site import contractorfacts as cf

pytestmark = pytest.mark.unit


def test_a_fact_absent_from_the_text_is_never_found():
    assert cf.found("A neighbourhood restaurant serving dinner nightly.") == ()


def test_licensed_and_insured_is_found_verbatim():
    assert "licensed_insured" in cf.found(
        "Our technicians are licensed and insured for your protection.")
    assert "licensed_insured" in cf.found("Fully licensed & insured plumbers.")


def test_emergency_availability_needs_the_actual_phrase():
    assert "emergency" in cf.found("24/7 emergency service, every day of the year.")
    assert "emergency" in cf.found("We offer around-the-clock repair.")
    assert "emergency" not in cf.found("Open Monday through Friday, 9 to 5.")


def test_warranty_is_found_but_not_confused_with_generic_praise():
    assert "warranty" in cf.found("Every installation carries a 5-year warranty.")
    assert "warranty" not in cf.found(
        "Our team is warm, friendly, and easy to work with.")


def test_free_estimate_needs_the_actual_offer():
    assert "free_estimate" in cf.found("Call today for a free estimate.")
    assert "free_estimate" not in cf.found("Our estimates are always accurate.")


def test_a_business_that_says_nothing_gets_nothing():
    """The floor. A page with real material but none of these four phrases in
    it must come back empty, not with a guess dressed as a fact."""
    text = ("We've been serving the Frisco area since our founding, with a "
            "team that takes pride in every job.")
    assert cf.found(text) == ()


def test_multiple_facts_come_back_in_a_stable_order():
    """Downstream reads this list positionally (`render._credentials`
    chooses its composition by `len(present)`), so the order has to be part
    of the contract, not an accident of dict iteration."""
    text = ("Licensed and insured. Free estimate on every job. Ask about our "
            "workmanship warranty. We answer 24/7 emergency calls.")
    assert cf.found(text) == (
        "licensed_insured", "emergency", "warranty", "free_estimate")


def test_every_fact_has_a_label():
    for fact in cf.FACTS:
        assert cf.label_for(fact.key) == fact.label
