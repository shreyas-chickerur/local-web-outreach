"""Versioned site storage."""

from __future__ import annotations

import pytest

from app.store import db, leads, sites

pytestmark = pytest.mark.unit


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(tmp_path / "t.db")
    yield connection
    connection.close()


@pytest.fixture()
def lead(conn):
    return leads.save_brief(conn, {"name": "Test Co", "location": "Frisco, TX",
                                   "facts": [], "open_questions": []})


def test_each_build_is_a_new_version(conn, lead):
    assert sites.save(conn, lead, "<html>one</html>", "warm") == 1
    assert sites.save(conn, lead, "<html>two</html>", "dark") == 2
    assert [v["version"] for v in sites.versions(conn, lead)] == [2, 1]


def test_an_earlier_version_is_still_there(conn, lead):
    """Iterating only helps if you can go back to the one that was better."""
    sites.save(conn, lead, "<html>one</html>", "warm")
    sites.save(conn, lead, "<html>two</html>", "dark")
    assert sites.html_for(conn, lead, 1) == "<html>one</html>"
    assert sites.html_for(conn, lead) == "<html>two</html>"      # latest by default


def test_building_a_site_lands_in_the_lead_trail(conn, lead):
    """Building someone a site is not a smaller event than fixing their phone."""
    sites.save(conn, lead, "<html/>", "warm and rustic")
    entry = leads.events(conn, lead)[0]
    assert entry["kind"] == "site" and entry["new_value"] == "v1"
    assert entry["note"] == "warm and rustic"
    assert entry["actor"]


def test_a_lead_with_no_site_returns_nothing_rather_than_failing(conn, lead):
    assert sites.html_for(conn, lead) is None
