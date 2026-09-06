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


def test_a_filename_that_says_what_it_shows_is_offered_as_a_description():
    """Their own uploads are often named after the subject, so those can be
    filled in without anyone squinting at a thumbnail."""
    assert photos.suggest_from_url("https://x/Short-Rib-980x1165.jpg") == "short rib"
    assert photos.suggest_from_url("https://x/housemade-bread.jpg") == "housemade bread"


def test_an_opaque_filename_offers_nothing_rather_than_a_guess():
    """A proxied Google photo has no name, and inventing one would be worse
    than leaving the field empty."""
    assert photos.suggest_from_url("/photo/1/0") == ""
    assert photos.suggest_from_url("https://x/IMG-0959-scaled.jpg") == ""
    assert photos.suggest_from_url("https://x/mg_2795.jpeg") == ""


def test_suggestions_stay_silent_about_what_they_cannot_read():
    urls = ["/photo/1/0", "https://x/garden-tomatoes.jpg"]
    assert photos.suggest_all(urls) == {
        "https://x/garden-tomatoes.jpg": "garden tomatoes"}
