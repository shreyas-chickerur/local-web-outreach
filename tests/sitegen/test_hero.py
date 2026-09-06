"""Choosing the lead photograph.

Every test here is a bug that shipped. The hero picker had six independent
faults that compounded, and the visible symptom of all of them was the same:
it chose Google photograph zero, whatever that happened to be.
"""

from __future__ import annotations

import pytest

import app.site.render as render
from app.site.render import (
    HERO_MIN_WIDTH,
    hero_scores,
    hero_table,
    pick_hero,
    trade_kind,
)

pytestmark = pytest.mark.unit


def sizes(mapping):
    return lambda url: mapping.get(url)


def test_a_perfect_crop_beats_a_bigger_near_square():
    """The old sort was lexicographic — width first, aspect only breaking exact
    ties — so a 3000x2900 beat a 2400x1350 that crops perfectly. The docstring
    claimed otherwise."""
    look = sizes({"/square": (3000, 2900), "/wide": (2400, 1350)})
    assert pick_hero(("/square", "/wide"), size_of=look) == "/wide"


def test_resolution_still_matters_at_equal_shape():
    look = sizes({"/small": (1200, 675), "/big": (3200, 1800)})
    assert pick_hero(("/small", "/big"), size_of=look) == "/big"


def test_a_portrait_never_leads():
    look = sizes({"/tall": (2000, 3000), "/wide": (1700, 1000)})
    assert pick_hero(("/tall", "/wide"), size_of=look) == "/wide"


def test_a_label_does_not_override_measured_quality():
    """A 900px blurry "dish" used to outrank an unlabelled 3200px perfectly
    composed room shot, purely for having been labelled. Quality and subject
    are terms in one score, not a strict precedence."""
    look = sizes({"/tiny-dish": (900, 600), "/big-room": (3200, 1800)})
    chosen = pick_hero(("/tiny-dish", "/big-room"),
                       labels={"/tiny-dish": "dish"}, trade="food",
                       size_of=look)
    assert chosen == "/big-room"


def test_a_label_still_decides_between_comparable_photographs():
    """The operator's judgement outranks the machine's when the machine has no
    reason to disagree."""
    look = sizes({"/room": (2400, 1400), "/dish": (2400, 1400)})
    chosen = pick_hero(("/room", "/dish"),
                       labels={"/room": "room", "/dish": "dish"},
                       trade="food", size_of=look)
    assert chosen == "/dish"


def test_a_logo_is_never_the_lead_however_large():
    look = sizes({"/logo": (4000, 2250), "/room": (1700, 1000)})
    chosen = pick_hero(("/logo", "/room"), labels={"/logo": "logo"},
                       size_of=look)
    assert chosen == "/room"


def test_an_uncategorisable_description_is_not_a_veto():
    """`tag_for` returns "other" for anything the phrase table cannot read, and
    "other" used to sit in NEVER_LEADS — so a good photograph described in
    unfamiliar words was silently made ineligible."""
    look = sizes({"/other": (3200, 1800), "/small": (1700, 1000)})
    chosen = pick_hero(("/other", "/small"), labels={"/other": "other"},
                       size_of=look)
    assert chosen == "/other"


def test_every_photograph_is_considered_not_the_first_ten():
    """Google's photographs come first in the pool, so a business with ten of
    them never had one of its own site's pictures examined."""
    pool = tuple(f"/g{i}" for i in range(10)) + ("/theirs",)
    look = sizes({**{f"/g{i}": (1700, 1000) for i in range(10)},
                  "/theirs": (3200, 1800)})
    assert pick_hero(pool, size_of=look) == "/theirs"
    assert len(hero_scores(pool, size_of=look)) == 11


def test_ties_keep_the_pool_order_rather_than_sorting_by_name():
    """With nothing measurable to go on, Google's own ordering is the best
    signal there is — and the answer must not move between runs."""
    pool = ("/zebra", "/apple", "/mango")
    assert pick_hero(pool, size_of=lambda url: None) == "/zebra"


def test_the_offset_walks_the_ranking():
    look = sizes({"/a": (3200, 1800), "/b": (2400, 1350), "/c": (1700, 1000)})
    pool = ("/c", "/b", "/a")
    assert pick_hero(pool, 0, size_of=look) == "/a"
    assert pick_hero(pool, 1, size_of=look) == "/b"
    assert pick_hero(pool, 4, size_of=look) == "/b"      # wraps, never fails


def test_an_unmeasurable_pool_still_produces_a_hero():
    assert pick_hero(("/a", "/b"), size_of=lambda url: None) == "/a"


def test_no_photographs_is_no_hero():
    assert pick_hero((), size_of=lambda url: None) is None


def test_the_ranking_is_printable_as_reasons():
    """A score nobody can read is a tier with extra steps."""
    look = sizes({"/a": (3200, 1800), "/b": (900, 600)})
    table = hero_table(hero_scores(("/a", "/b"), size_of=look))
    assert "resolution" in table and "aspect" in table and "subject" in table
    assert "3200x1800" in table
    assert table.index("/a") < table.index("/b")


@pytest.mark.parametrize("trade,kind", [
    ("Japanese Restaurant", "food"), ("Coffee Shop", "food"),
    ("Barber Shop", "groom"), ("Nail Salon", "groom"),
    ("Dentist", "care"), ("Chiropractic Clinic", "care"),
    ("Law Firm", "desk"), ("Insurance Agency", "desk"),
    ("Yoga Studio", "body"), ("Roofing Contractor", "trade"),
    ("Auto Repair Shop", "trade"), ("Hardware Store", "retail"),
    ("", "default"),
])
def test_a_business_lands_in_the_right_bucket(trade, kind):
    """There were three buckets, so a salon, a dentist, a law firm and a gym
    all preferred a room shot — right for exactly one of them."""
    assert trade_kind(trade) == kind


def test_a_dentist_leads_with_a_person_and_a_restaurant_with_a_plate():
    look = sizes({"/people": (2400, 1400), "/dish": (2400, 1400)})
    labels = {"/people": "people", "/dish": "dish"}
    pool = ("/people", "/dish")
    assert pick_hero(pool, labels=labels, trade="care", size_of=look) == "/people"
    assert pick_hero(pool, labels=labels, trade="food", size_of=look) == "/dish"


def test_material_measures_proxied_photographs_without_asking_our_own_server():
    """The bug behind the whole complaint: a proxied /photo/<lead>/<n> was
    measured by an HTTP request to a hardcoded port, which answered None from
    the command line, from a test, and from inside a live request."""
    assert not hasattr(render, "LOCAL")
    material = render.Material(name="x", lead_id=7, place_photos=("places/a",))
    # No API key in the test environment, so the fetch declines rather than
    # reaching out — the point is that it never builds a self-addressed URL.
    assert material.size_of("/photo/7/0") is None
    assert material.size_of("/photo/7/99") is None


def test_the_minimum_width_is_a_curve_not_a_cliff():
    """Below the floor a photograph is penalised, not excluded: a business
    whose pictures are all small must still get a hero."""
    look = sizes({"/a": (1000, 600), "/b": (1200, 700)})
    assert pick_hero(("/a", "/b"), size_of=look) == "/b"
    assert HERO_MIN_WIDTH == 1600


# --- what only looking at the picture can establish ---------------------- #

def seen(**kw):
    base = {"quality": 3, "is_hero_candidate": True, "has_text_overlay": False,
            "is_logo_or_badge": False, "is_screenshot_or_document": False,
            "headline_region_luminance": "mixed"}
    return {**base, **kw}


def test_a_photograph_of_words_never_leads():
    """The events banner: a picture with a sentence set across it, cropped
    mid-word. Nothing but looking can tell."""
    look = sizes({"/banner": (3200, 1800), "/plain": (1700, 1000)})
    chosen = pick_hero(("/banner", "/plain"), size_of=look, vision={
        "/banner": seen(quality=5, has_text_overlay=True),
        "/plain": seen(quality=3)})
    assert chosen == "/plain"


@pytest.mark.parametrize("flag", ["has_text_overlay", "is_logo_or_badge",
                                  "is_screenshot_or_document"])
def test_each_disqualifier_costs_more_than_any_amount_of_sharpness(flag):
    look = sizes({"/bad": (3200, 1800), "/ok": (1650, 950)})
    chosen = pick_hero(("/bad", "/ok"), size_of=look, vision={
        "/bad": seen(quality=5, **{flag: True}), "/ok": seen(quality=2)})
    assert chosen == "/ok"


def test_quality_separates_two_photographs_of_the_same_shape():
    look = sizes({"/blurry": (2400, 1400), "/sharp": (2400, 1400)})
    chosen = pick_hero(("/blurry", "/sharp"), size_of=look, vision={
        "/blurry": seen(quality=1), "/sharp": seen(quality=5)})
    assert chosen == "/sharp"


def test_a_bright_headline_region_loses_to_a_dark_one():
    """White type over a bright sky is unreadable, and the region under the
    headline is the only part of the frame that decides it."""
    look = sizes({"/sky": (2400, 1400), "/shade": (2400, 1400)})
    chosen = pick_hero(("/sky", "/shade"), size_of=look, vision={
        "/sky": seen(headline_region_luminance="bright"),
        "/shade": seen(headline_region_luminance="dark")})
    assert chosen == "/shade"


def test_without_a_key_no_photograph_is_penalised_for_the_absence():
    """A lead built with no vision must rank on shape and size alone, not
    have every candidate marked down for a call that never happened."""
    look = sizes({"/a": (3200, 1800), "/b": (1700, 1000)})
    assert pick_hero(("/a", "/b"), size_of=look, vision={}) == "/a"
    assert pick_hero(("/a", "/b"), size_of=look, vision=None) == "/a"


def test_an_uncategorised_label_is_outvoted_by_measurement():
    """Now that vision writes the subject, `tag_for` only ever sees operator
    free text — so "other" means "I did not recognise these words", never "bad
    photograph". It is a penalty of about a tenth, which resolution and vision
    quality both outrank by an order of magnitude."""
    from app.site.render import _subject_term
    assert _subject_term("other", "food") < _subject_term(None, "food")
    assert _subject_term("other", "food") > _subject_term("logo", "food")

    # Size outvotes it.
    look = sizes({"/other": (3200, 1800), "/plain": (1700, 1000)})
    assert pick_hero(("/other", "/plain"), labels={"/other": "other"},
                     size_of=look) == "/other"
    # Vision quality outvotes it.
    same = sizes({"/other": (2400, 1400), "/plain": (2400, 1400),
                  "/dish": (2400, 1400)})
    assert pick_hero(("/other", "/plain"), labels={"/other": "other"},
                     size_of=same, vision={"/other": seen(quality=5),
                                           "/plain": seen(quality=1)}) == "/other"
    # A real subject match still wins when nothing else separates them.
    assert pick_hero(("/other", "/dish"),
                     labels={"/other": "other", "/dish": "dish"},
                     trade="food", size_of=same) == "/dish"


# --- ported from tests/store/test_photos.py ------------------------------ #
# These cases were asserting against `rank_for_hero`, which nothing in app/
# called any more: green against a path production no longer ran. The cases
# themselves are good, so they now run against the scorer that decides.

def same_size(*urls):
    return sizes({url: (2400, 1400) for url in urls})


def test_neither_a_logo_nor_an_award_badge_leads():
    urls = ("badge", "mark", "plate")
    labels = {"badge": "award", "mark": "logo", "plate": "dish"}
    assert pick_hero(urls, labels=labels, trade="food",
                     size_of=same_size(*urls)) == "plate"


def test_a_restaurant_leads_with_a_plate_or_the_room():
    urls = ("peppers", "plate", "dining", "sign")
    labels = {"peppers": "ingredients", "plate": "dish", "dining": "room",
              "sign": "exterior"}
    assert pick_hero(urls, labels=labels, trade="food",
                     size_of=same_size(*urls)) == "plate"


def test_a_trade_leads_with_finished_work_not_a_plate():
    urls = ("plate", "roof")
    labels = {"plate": "dish", "roof": "work"}
    assert pick_hero(urls, labels=labels, trade="trade",
                     size_of=same_size(*urls)) == "roof"


def test_an_unknown_subject_beats_a_known_unsuitable_one():
    urls = ("logo", "peppers", "unlabelled")
    labels = {"logo": "logo", "peppers": "ingredients"}
    assert pick_hero(urls, labels=labels, trade="food",
                     size_of=same_size(*urls)) == "unlabelled"


def test_an_unlabelled_pool_keeps_its_original_order():
    """A business nobody has labelled should still get a page, in the order the
    photographs arrived — which for Google's is its own ranking."""
    urls = ("a", "b", "c")
    scored = hero_scores(urls, size_of=same_size(*urls))
    assert [s.url for s in scored] == list(urls)


def test_an_untagged_photograph_is_still_a_candidate():
    """"I could not identify this one" keeps the picture in the gallery rather
    than throwing it away — but the known one leads."""
    urls = ("/photo/1/0", "/photo/1/5")
    scored = hero_scores(urls, labels={"/photo/1/0": "room"}, trade="food",
                         size_of=same_size(*urls))
    assert {s.url for s in scored} == set(urls)
    assert scored[0].url == "/photo/1/0"
