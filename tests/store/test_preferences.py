"""Repeated operator preferences, accumulated across leads (Slice H, item 4)."""

from __future__ import annotations

import pytest

from app.store import db, leads, preferences

pytestmark = pytest.mark.unit


@pytest.fixture
def conn():
    with db.session(":memory:") as connection:
        yield connection


_next_name = iter(f"Business {n}" for n in range(10_000))


def _lead(conn) -> int:
    """A genuinely distinct lead each call — `save_brief` dedupes by
    (name, location), so a fixed name would collapse every "several
    leads" test back onto the same one."""
    return leads.save_brief(
        conn, {"name": next(_next_name), "facts": [], "published": {}})


def test_a_phrase_said_on_one_lead_is_not_yet_a_preference(conn):
    lead = _lead(conn)
    preferences.record(conn, lead, ["opened warm"])
    assert preferences.repeated(conn, min_leads=3) == []


def test_a_phrase_said_on_three_distinct_leads_is_a_preference(conn):
    for _ in range(3):
        lead = _lead(conn)
        preferences.record(conn, lead, ["opened warm"])
    assert preferences.repeated(conn, min_leads=3) == ["opened warm"]


def test_saying_it_three_times_on_the_same_lead_does_not_count(conn):
    """A preference is expressed across SEVERAL LEADS, not one conversation
    repeating itself — three instructions on one business are one signal,
    not three."""
    lead = _lead(conn)
    preferences.record(conn, lead, ["opened warm"])
    preferences.record(conn, lead, ["opened warm"])
    preferences.record(conn, lead, ["opened warm"])
    assert preferences.repeated(conn, min_leads=3) == []


def test_empty_and_blank_phrases_record_nothing(conn):
    lead = _lead(conn)
    preferences.record(conn, lead, ["", "   ", None])  # type: ignore[list-item]
    rows = conn.execute("SELECT COUNT(*) AS n FROM preferences").fetchone()
    assert rows["n"] == 0


def test_most_repeated_comes_first(conn):
    for _ in range(4):
        lead = _lead(conn)
        preferences.record(conn, lead, ["opened warm"])
    for _ in range(3):
        lead = _lead(conn)
        preferences.record(conn, lead, ["led with reviews"])
    assert preferences.repeated(conn, min_leads=3) == [
        "opened warm", "led with reviews"]
