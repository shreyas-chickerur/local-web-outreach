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


def test_a_label_is_remembered_against_the_lead(conn, lead):
    photos.label(conn, lead, "/photo/1/0", "dish", actor="shreyas")
    assert photos.labels_for(conn, lead) == {"/photo/1/0": "dish"}


def test_relabelling_replaces_rather_than_duplicates(conn, lead):
    photos.label(conn, lead, "/photo/1/0", "dish")
    photos.label(conn, lead, "/photo/1/0", "room")
    assert photos.labels_for(conn, lead) == {"/photo/1/0": "room"}


def test_an_unknown_label_is_refused(conn, lead):
    with pytest.raises(ValueError, match="unknown label"):
        photos.label(conn, lead, "/photo/1/0", "delicious")


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
