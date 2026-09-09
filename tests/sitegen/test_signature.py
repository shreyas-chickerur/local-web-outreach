"""`signature.py`'s devices, unit-tested directly.

The gap this closes: `tests/test_no_unverified_credential_ships.py` replays
frozen directions from the committed fixtures, so it cannot see a
regression in `_stamp_corroborated` until after a `--redecide` re-freezes
the corpus around it — a guard that only fails a day late. This is the
same check, run directly against `available()` and `_stamp_corroborated()`
with a business built for the purpose, so a revert fails here, now, with no
model call and no redecide needed to notice.
"""

from __future__ import annotations

import pytest

from app.site import signature as sig
from app.site.render import Material

pytestmark = pytest.mark.unit


def _plumber(about: str = "") -> Material:
    return Material(name="Test Plumbing", trade="Plumber", about=about,
                    rating=4.8, reviews=100)


def test_stamp_is_corroborated_when_the_business_says_so():
    m = _plumber("Licensed and insured technicians on every call.")
    assert sig._stamp_corroborated(m)
    assert "stamp" in sig.available(m, 6)


def test_stamp_is_not_corroborated_when_the_business_says_nothing():
    m = _plumber("We are Frisco's trusted plumbing team.")
    assert not sig._stamp_corroborated(m)
    assert "stamp" not in sig.available(m, 6)


def test_stamp_is_not_corroborated_with_no_text_at_all():
    """`threadbare`'s own shape — no about text, no content blocks — is
    exactly the case that shipped uncorroborated. This is that case,
    isolated."""
    m = _plumber("")
    assert not sig._stamp_corroborated(m)
    assert "stamp" not in sig.available(m, 6)


def test_render_never_prints_the_mark_for_an_uncorroborated_business():
    m = _plumber("We are Frisco's trusted plumbing team.")
    assert sig.render("stamp", m) == ""


def test_render_prints_the_corroborated_mark():
    m = _plumber("Licensed and insured technicians on every call.")
    page = sig.render("stamp", m)
    assert "Licensed &amp; insured" in page
    assert page.count("<span>") == 4


def test_care_and_desk_have_their_own_corroborating_fact():
    """The two facts added alongside the existing trade one — a dentist's
    or a lawyer's own text has to say so too, not borrow the contractor's
    phrasing."""
    dentist = Material(name="Test Dental", trade="Dentist", rating=4.5,
                       reviews=50, about="A registered practice serving "
                       "the whole family.")
    assert sig._stamp_corroborated(dentist)

    lawyer = Material(name="Test Law", trade="Attorney", rating=4.9,
                      reviews=200, about="Our attorneys are admitted to "
                      "the bar in three states.")
    assert sig._stamp_corroborated(lawyer)

    silent_dentist = Material(name="Quiet Dental", trade="Dentist",
                              rating=4.5, reviews=50,
                              about="We care about your smile.")
    assert not sig._stamp_corroborated(silent_dentist)
