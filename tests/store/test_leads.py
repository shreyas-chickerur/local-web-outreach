"""The lead store and its audit trail.

What you were told at a business's front door is the most valuable thing in
this system and the only part that cannot be re-fetched, so these tests pin the
ways it could be lost: overwritten by a re-run, silently replaced, or recorded
without saying who said so.
"""

from __future__ import annotations

import pytest

from app.store import db, leads

pytestmark = pytest.mark.unit


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(tmp_path / "t.db")
    yield connection
    connection.close()


def _brief(**kw) -> dict:
    base = {
        "name": "Ryno Lawn Care", "location": "Frisco, TX",
        "website_url": "https://rynolawncare.com",
        "facts": [{"field": "hours", "label": "Hours", "value": "Mon-Fri 8am-5pm",
                   "confidence": "conflict", "score": 30, "corroborations": 2,
                   "sources": [], "candidates": [], "dissent": []}],
        "open_questions": ["What are their opening hours?"],
        "assumptions": [], "sources_consulted": ["google"], "chain_signals": [],
        "ratings": [], "published": None,
    }
    return {**base, **kw}


def test_the_same_business_typed_differently_is_one_lead(conn):
    first = leads.save_brief(conn, _brief(name="Ryno Lawn Care"))
    second = leads.save_brief(conn, _brief(name="ryno lawn care"))
    assert first == second


def test_confirming_a_field_overrides_the_sources_and_names_you(conn):
    lead = leads.save_brief(conn, _brief())
    leads.verify(conn, lead, "hours", "Mon-Sat 7am-6pm",
                 note="asked at the counter", actor="shreyas")

    brief = leads.brief_with_overrides(conn, lead)
    hours = next(f for f in brief["facts"] if f["field"] == "hours")
    assert hours["value"] == "Mon-Sat 7am-6pm"
    assert hours["confidence"] == "operator_verified"
    assert hours["verified_by"] == "shreyas"
    assert hours["verified_note"] == "asked at the counter"
    # What the sources said is not erased by your correction.
    assert hours["superseded"] == "Mon-Fri 8am-5pm"
    # A question you have answered is no longer a question.
    assert brief["open_questions"] == []


def test_confirming_what_the_sources_already_said_is_not_a_correction(conn):
    """The trail should not imply a value changed when it did not."""
    lead = leads.save_brief(conn, _brief())
    leads.verify(conn, lead, "hours", "Mon-Fri 8am-5pm", note="confirmed by phone")
    assert leads.events(conn, lead)[0]["kind"] == "verified"

    leads.verify(conn, lead, "hours", "Mon-Sat 7am-6pm", note="they changed it")
    assert leads.events(conn, lead)[0]["kind"] == "corrected"


def test_re_running_the_research_keeps_what_you_were_told(conn):
    """Research is disposable; a conversation at the door is not."""
    lead = leads.save_brief(conn, _brief())
    leads.verify(conn, lead, "hours", "Mon-Sat 7am-6pm", note="asked in person")
    leads.set_status(conn, lead, "visited")

    # A later lookup returns fresh, different directory data.
    again = leads.save_brief(conn, _brief(facts=[
        {"field": "hours", "label": "Hours", "value": "Mon-Sun 9am-9pm",
         "confidence": "verified", "score": 90, "corroborations": 2,
         "sources": [], "candidates": [], "dissent": []}]))
    assert again == lead

    brief = leads.brief_with_overrides(conn, lead)
    hours = next(f for f in brief["facts"] if f["field"] == "hours")
    assert hours["value"] == "Mon-Sat 7am-6pm"
    assert hours["superseded"] == "Mon-Sun 9am-9pm"
    assert brief["status"] == "visited"


def test_the_latest_statement_wins_and_the_earlier_one_survives(conn):
    lead = leads.save_brief(conn, _brief())
    leads.verify(conn, lead, "phone", "(111) 111-1111", note="first")
    leads.verify(conn, lead, "phone", "(222) 222-2222", note="they corrected me")

    brief = leads.brief_with_overrides(conn, lead)
    phone = next(f for f in brief["facts"] if f["field"] == "phone")
    assert phone["value"] == "(222) 222-2222"
    # Nothing is ever updated or deleted: both statements remain readable.
    notes = [e["note"] for e in leads.events(conn, lead)]
    assert "first" in notes and "they corrected me" in notes


def test_a_field_nobody_published_can_still_be_established(conn):
    lead = leads.save_brief(conn, _brief(facts=[]))
    leads.verify(conn, lead, "phone", "(469) 496-2778", note="on their van")
    brief = leads.brief_with_overrides(conn, lead)
    assert [f["value"] for f in brief["facts"]] == ["(469) 496-2778"]


def test_a_blank_confirmation_is_refused(conn):
    lead = leads.save_brief(conn, _brief())
    with pytest.raises(ValueError):
        leads.verify(conn, lead, "hours", "   ")


def test_an_unknown_field_or_status_is_refused(conn):
    lead = leads.save_brief(conn, _brief())
    with pytest.raises(ValueError):
        leads.verify(conn, lead, "favourite_colour", "blue")
    with pytest.raises(ValueError):
        leads.set_status(conn, lead, "definitely buying")


def test_every_event_records_who_and_when(conn):
    lead = leads.save_brief(conn, _brief())
    leads.verify(conn, lead, "hours", "Mon-Sat 7am-6pm", actor="shreyas")
    leads.set_status(conn, lead, "visited")
    leads.record(conn, lead, "note", note="owner is Allison")

    for event in leads.events(conn, lead):
        assert event["actor"]
        assert event["at"].startswith("20")
