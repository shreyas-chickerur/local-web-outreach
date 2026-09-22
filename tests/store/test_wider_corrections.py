"""Section B: what can be corrected, and whether a correction reaches anything.

Every test here crosses a seam that was previously untested: the operator's
event table to the brief the generator reads, and the brief the checks judge
against.
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


def _lead(conn) -> int:
    return leads.save_brief(conn, {
        "name": "Acme Roofing",
        "location": "Frisco, TX",
        "website_url": "https://acme.test/",
        "facts": [{"field": "phone", "value": "(111) 111-1111",
                   "confidence": "verified", "score": 90}],
        "published": {
            "tagline": "Roofing since 1994.",
            "about": "We started in a garage.",
            "services": ["Roof repair", "Gutters"],
            "emails": [],
            "socials": [{"name": "Facebook", "url": "https://facebook.com/acme"}],
            "menu_items": [],
            "photos": ["https://acme.test/1.jpg"],
        },
        "assumptions": [], "open_questions": [], "sources_consulted": [],
    })


def test_the_four_fields_are_now_twelve():
    assert set(leads.VERIFIABLE_FACTS) <= set(leads.VERIFIABLE)
    for field in ("tagline", "about", "services", "email", "photos",
                  "menu_items", "socials", "name"):
        assert field in leads.VERIFIABLE


def test_correcting_a_tagline_reaches_what_generation_reads(conn):
    """The seam: an event row must change `published`, not only `facts`.

    Generation reads `brief["published"]["tagline"]`. An override that stopped
    at `facts` changed a screen and nothing a visitor would ever see.
    """
    lead = _lead(conn)
    leads.verify(conn, lead, "tagline", "Roofing across North Texas since 1994.",
                 note="the owner said the old one was written by a cousin")
    brief = leads.brief_with_overrides(conn, lead)
    assert brief["published"]["tagline"] == "Roofing across North Texas since 1994."
    assert brief["published_superseded"]["tagline"] == "Roofing since 1994."


def test_a_list_is_typed_one_per_line_and_stored_as_a_list(conn):
    lead = _lead(conn)
    leads.verify(conn, lead, "services",
                 "Roof repair\nRoof replacement\nStorm damage")
    published = leads.brief_with_overrides(conn, lead)["published"]
    assert published["services"] == ["Roof repair", "Roof replacement",
                                     "Storm damage"]


def test_menu_items_keep_the_shape_the_page_renders(conn):
    """A page reads name, price and description. Text in must come back as that."""
    lead = _lead(conn)
    leads.verify(conn, lead, "menu_items",
                 "Short Rib — $32 — braised overnight\nSpaetzle $18")
    items = leads.brief_with_overrides(conn, lead)["published"]["menu_items"]
    assert items[0] == {"name": "Short Rib", "price": "$32",
                        "description": "braised overnight"}
    assert items[1]["name"] == "Spaetzle"


def test_a_social_link_without_a_platform_name_takes_it_from_the_host(conn):
    lead = _lead(conn)
    leads.verify(conn, lead, "socials",
                 "https://www.instagram.com/acme/\nFacebook https://facebook.com/acme")
    links = leads.brief_with_overrides(conn, lead)["published"]["socials"]
    assert links[0] == {"name": "Instagram", "url": "https://www.instagram.com/acme/"}
    assert links[1]["name"] == "Facebook"


def test_the_business_name_itself_can_be_corrected(conn):
    lead = _lead(conn)
    leads.verify(conn, lead, "name", "Acme Roofing & Gutters")
    assert leads.brief_with_overrides(conn, lead)["name"] == "Acme Roofing & Gutters"


def test_what_the_screen_offers_says_how_it_was_established(conn):
    lead = _lead(conn)
    rows = {r["field"]: r for r in leads.brief_with_overrides(conn, lead)["confirmable"]}
    assert rows["tagline"]["confidence"] == "unverified"
    assert rows["email"]["confidence"] == "missing"
    assert rows["services"]["value"] == "Roof repair\nGutters"
    assert rows["services"]["count"] == 2
    leads.verify(conn, lead, "tagline", "New words.", note="told at the door")
    again = {r["field"]: r for r in leads.brief_with_overrides(conn, lead)["confirmable"]}
    assert again["tagline"]["confidence"] == "operator_verified"
    assert again["tagline"]["superseded"] == "Roofing since 1994."


def test_verify_says_whether_anything_actually_changed(conn):
    """What happens next depends on it: only a correction rebuilds a page."""
    lead = _lead(conn)
    first = leads.verify(conn, lead, "phone", "(222) 222-2222")
    assert first["kind"] == "corrected"
    assert first["was"] == "(111) 111-1111"
    assert leads.verify(conn, lead, "phone", "(222) 222-2222")["kind"] == "verified"


def test_a_re_crawl_does_not_erase_a_correction(conn):
    """`save_brief` refreshes the sources; the trail outranks them afterwards."""
    lead = _lead(conn)
    leads.verify(conn, lead, "tagline", "What the owner actually says.")
    leads.save_brief(conn, {
        "name": "Acme Roofing", "location": "Frisco, TX",
        "website_url": "https://acme.test/",
        "facts": [], "published": {"tagline": "A newly crawled tagline."},
        "assumptions": [], "open_questions": [], "sources_consulted": [],
    })
    brief = leads.brief_with_overrides(conn, lead)
    assert brief["published"]["tagline"] == "What the owner actually says."
    assert brief["published_superseded"]["tagline"] == "A newly crawled tagline."


def test_an_unknown_field_is_still_refused(conn):
    lead = _lead(conn)
    with pytest.raises(ValueError):
        leads.verify(conn, lead, "favourite_colour", "blue")
