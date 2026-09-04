"""What a photograph shows, according to a person.

Shape is measurable; subject matter is not. A landscape shot of raw peppers is
the wrong lead for a dining room, and no filename parsing finds that out.
"""

from __future__ import annotations

import pytest

from app.store import db, leads, photos

pytestmark = pytest.mark.unit


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(tmp_path / "t.db")
    yield connection
    connection.close()


@pytest.fixture()
def lead(conn):
    return leads.save_brief(conn, {"name": "Test Co", "facts": []})


def test_a_description_is_kept_and_tagged(conn, lead):
    """The words are the point: they become alt text, which every generated
    image had been shipping empty."""
    photos.label(conn, lead, "/photo/1/0", "brisket plate with slaw",
                 actor="shreyas")
    said = photos.described(conn, lead)["/photo/1/0"]
    assert said["label"] == "dish"
    assert said["description"] == "brisket plate with slaw"


def test_relabelling_replaces_rather_than_duplicates(conn, lead):
    photos.label(conn, lead, "/photo/1/0", "a plate of food")
    photos.label(conn, lead, "/photo/1/0", "the dining room")
    assert photos.labels_for(conn, lead) == {"/photo/1/0": "room"}


def test_the_derived_tag_can_be_overridden(conn, lead):
    """The parse gets things wrong, and the person looking at the photograph
    is right."""
    photos.label(conn, lead, "/photo/1/0", "the bar at night", what="people")
    assert photos.labels_for(conn, lead)["/photo/1/0"] == "people"


def test_an_unknown_override_is_refused(conn, lead):
    with pytest.raises(ValueError, match="unknown label"):
        photos.label(conn, lead, "/photo/1/0", "a plate", what="delicious")


def test_an_empty_description_with_no_override_is_refused(conn, lead):
    with pytest.raises(ValueError, match="describe"):
        photos.label(conn, lead, "/photo/1/0", "   ")


@pytest.mark.parametrize("words,tag", [
    ("james beard award badge", "award"),
    ("our logo", "logo"),
    ("chef in the kitchen", "people"),
    ("a cocktail on the bar", "drink"),
    ("housemade bread on a table", "dish"),
    ("raw peppers from the farm", "ingredients"),
    ("the front of the building", "exterior"),
    ("the dining room at night", "room"),
])
def test_free_text_is_tagged_specific_before_generic(words, tag):
    """Ordering is the whole design: put the generic room words first and
    "chef in the kitchen" becomes a photograph of a room."""
    assert photos.tag_for(words) == tag


def test_an_award_badge_is_told_apart_from_a_company_logo():
    """Both are marks rather than photographs, but one belongs large in the
    recognition band and the other belongs in the nav."""
    assert photos.tag_for("james beard nominee badge") == "award"
    assert photos.tag_for("the company logo in black") == "logo"


def test_neither_a_logo_nor_an_award_badge_leads():
    urls = ["badge", "mark", "plate"]
    labels = {"badge": "award", "mark": "logo", "plate": "dish"}
    assert photos.rank_for_hero(urls, labels, "food")[0] == "plate"


def test_a_restaurant_leads_with_a_plate_or_the_room():
    urls = ["peppers", "plate", "dining", "sign"]
    labels = {"peppers": "ingredients", "plate": "dish", "dining": "room",
              "sign": "exterior"}
    assert photos.rank_for_hero(urls, labels, "food")[0] == "plate"


def test_a_trade_leads_with_finished_work_not_a_plate():
    urls = ["plate", "roof"]
    labels = {"plate": "dish", "roof": "exterior"}
    assert photos.rank_for_hero(urls, labels, "trade")[0] == "roof"


def test_ingredients_and_logos_never_lead():
    urls = ["logo", "peppers", "unlabelled"]
    labels = {"logo": "logo", "peppers": "ingredients"}
    ranked = photos.rank_for_hero(urls, labels, "food")
    assert ranked[0] == "unlabelled"        # unknown beats known-unsuitable


def test_an_unlabelled_lead_keeps_its_original_order():
    """A business nobody has labelled should still get a page."""
    urls = ["a", "b", "c"]
    assert photos.rank_for_hero(urls, {}, "food") == urls
