"""The design audit: defects the operator should never have to catch.

Everything checked here is objectively wrong rather than a matter of taste —
contrast below the threshold, a picture used twice, a hover that promises a
link it does not have. Taste stays with the person; defects stop here.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.site.audit import AuditReport, audit, check_contrast, check_copy, check_layout
from app.site.render import build
from app.site.theme import THEMES, contrast, theme_for

pytestmark = pytest.mark.unit

BRIEF = {"name": "Test Co", "facts": [],
         "published": {"services": ["A", "B", "C"], "products": [],
                       "menu_items": [], "hours": [], "photos": [],
                       "socials": [], "emails": [], "tagline": "Hello"},
         "ratings": []}


@pytest.mark.parametrize("mood", list(THEMES))
def test_every_theme_passes_its_own_audit(mood):
    """The build should never hand over a page with a known defect in it."""
    page, spec = build(BRIEF, mood)
    report = audit(page, theme_for(spec.mood))
    assert report.clean, [str(f) for f in report.failures]


def test_a_declared_colour_that_is_too_pale_is_caught():
    """Grounds are safe by construction — `on()` computes their foreground. The
    audit exists for the colours that are still *declared*: secondary text and
    the accent. A pale grey dim is the classic way body copy goes unreadable."""
    broken = replace(THEMES["warm"], dim="#e6e0d6")
    report = AuditReport()
    check_contrast("", broken, report)
    assert any(f.rule == "contrast" for f in report.failures)
    assert "secondary text" in report.failures[0].detail


def test_computed_grounds_cannot_produce_the_cream_on_white_defect():
    """The defect that shipped: a foreground paired with one background while a
    specificity conflict handed it a different one. Computing the foreground
    from the ground that actually wins makes it unreachable."""
    for theme in THEMES.values():
        for ground in (theme.bg, theme.surface, theme.raise_, theme.accent):
            assert contrast(theme.on(ground), ground) >= 4.5


def test_readable_foregrounds_are_computed_not_paired():
    """Every ground in every theme resolves to something readable on it."""
    for theme in THEMES.values():
        for ground in (theme.bg, theme.surface, theme.raise_, theme.accent):
            assert contrast(theme.on(ground), ground) >= 4.5


def test_a_hover_that_promises_a_link_is_a_failure():
    page = "\n.offer:hover{transform:translateY(-6px);box-shadow:var(--lift)}"
    report = AuditReport()
    check_layout(page, report)
    assert any(f.rule == "affordance" for f in report.failures)


def test_a_stranded_grid_cell_is_reported():
    page = ('<section id="services">' + '<article class="offer">x</article>' * 4
            + "</section>")
    report = AuditReport()
    check_layout(page, report)
    assert any("stranded" in f.detail for f in report.findings)


def test_buzzwords_are_reported_but_never_rewritten():
    """The words are the business's own. Rewriting what someone says about
    themselves is precisely what this system must not do."""
    report = AuditReport()
    check_copy("<p>We seamlessly empower your synergy.</p>", report)
    rules = [f.rule for f in report.findings]
    assert rules.count("copy") >= 2
    assert not any(f.repaired for f in report.findings)


def test_a_limp_call_to_action_is_a_failure():
    report = AuditReport()
    check_copy('<a class="cta" href="#">Submit</a>', report)
    assert any(f.rule == "microcopy" for f in report.failures)
    report = AuditReport()
    check_copy('<a class="cta" href="tel:1">Book a table</a>', report)
    assert not report.failures


def test_no_photograph_is_used_twice():
    rich = dict(BRIEF)
    rich["lead_id"] = 3
    rich["place_photos"] = [f"places/x/photos/{n}" for n in range(9)]
    rich["published"] = {**BRIEF["published"], "blocks": [
        {"kind": "feature", "heading": "Dinner Service",
         "text": "We serve dinner nightly from a scratch kitchen downtown here.",
         "images": ["/photo/3/0"], "entries": []}]}
    page, spec = build(rich, "warm")
    report = audit(page, theme_for(spec.mood))
    assert not [f for f in report.findings if f.rule == "imagery"]


def test_the_report_separates_what_it_fixed_from_what_it_found():
    report = audit("<html></html>", THEMES["warm"],
                   repairs=["imagery: dropped a duplicate photograph"])
    payload = report.as_dict()
    assert payload["repairs"] == ["imagery: dropped a duplicate photograph"]
    assert "imagery" not in " ".join(payload["failures"])
