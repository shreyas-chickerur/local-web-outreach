"""BRIEF §5's contractor facts — eight of nine this generator ships. Each is
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


# ------------------------------------------------ the four newest facts --- #
# Patterns checked against the whole 19-fixture corpus before landing — an
# earlier, looser `service_area` pattern matched "great service you
# deserve" and "we must preserve the family dynamic" on businesses that
# never named a service area at all. These pin the precision, not just the
# recall.

def test_service_area_needs_a_real_trigger_phrase():
    assert "service_area" in cf.found(
        "What areas in Dallas do you serve? We serve Lakewood, Casa Linda, "
        "and surrounding neighborhoods.")
    assert "service_area" in cf.found("Proudly serving the greater DFW area.")
    assert "service_area" not in cf.found("We offer great service you deserve.")
    assert "service_area" not in cf.found(
        "We must preserve the family dynamic through this difficult time.")


def test_financing_is_found_but_not_confused_with_estimates():
    assert "financing" in cf.found("We have a great in-office payment plan.")
    assert "financing" in cf.found("Ask about financing options today.")
    assert "financing" not in cf.found("Call today for a free estimate.")


def test_manufacturer_badge_needs_a_named_certification():
    assert "manufacturer_badge" in cf.found(
        "As a VELUX Certified Installer, we bring natural light into your home.")
    assert "manufacturer_badge" in cf.found(
        "We are proud to be an authorized dealer for Trane products.")
    assert "manufacturer_badge" not in cf.found(
        "Our technicians are certified to handle any job.")


def test_response_time_needs_a_stated_window():
    assert "response_time" in cf.found("Same-Day Service on every call.")
    assert "response_time" in cf.found("We respond within 30 minutes.")
    assert "response_time" not in cf.found("We respond quickly to every call.")


def test_the_four_newest_facts_extend_the_stable_order():
    text = ("Licensed and insured. Free estimate on every job. Ask about "
            "our workmanship warranty. We answer 24/7 emergency calls. "
            "What areas do you serve? Financing options available. As a "
            "VELUX Certified Installer we install skylights. Same-Day "
            "Service guaranteed.")
    assert cf.found(text) == (
        "licensed_insured", "emergency", "warranty", "free_estimate",
        "service_area", "financing", "manufacturer_badge", "response_time")
