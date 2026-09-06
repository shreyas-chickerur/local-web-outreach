"""The build in stages, so a retry costs only what failed.

`workspace()` used to run the whole build inside a bare `except Exception:
pass` — twenty-five seconds, then a blank screen with nothing said about why,
while the operator is standing in someone's shop. And a failure in the last
stage threw away the vision pass and the design decision that preceded it, so
the retry paid for both again.
"""

from __future__ import annotations

import pytest

from app.site import pipeline
from app.site.pipeline import STAGES, BuildFailed, build_progress, run_stage
from app.store import db, leads, photos, sites

pytestmark = pytest.mark.unit

BRIEF = {
    "name": "The Heritage Table",
    "facts": [{"field": "phone", "value": "(469) 664-0100",
               "confidence": "verified"}],
    "published": {"tagline": "A neighbourhood restaurant.",
                  "photos": [f"https://x/{n}.jpg" for n in range(1, 5)],
                  "services": ["Dinner"], "hours": ["Mon-Sat 5pm-9pm"],
                  "menu_items": [], "blocks": [], "products": [],
                  "socials": [], "emails": [], "menu_media": []},
    "ratings": [{"source": "google", "value": 4.6, "reviews": 676}],
}


@pytest.fixture
def conn():
    with db.session(":memory:") as connection:
        yield connection


@pytest.fixture
def lead(conn):
    return leads.save_brief(conn, BRIEF)


@pytest.fixture
def looked(conn, lead, monkeypatch):
    """Vision answered, without a key or a call."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {
        url: {"subject": "dish", "quality": 4, "is_hero_candidate": True,
              "alt_text": "A plate of food"} for url in urls})
    return lead


def test_each_stage_runs_in_order_and_is_recorded(conn, looked):
    assert build_progress(conn, looked)["done"] == []
    for index, stage in enumerate(STAGES):
        run_stage(conn, looked, stage)
        assert build_progress(conn, looked)["done"] == list(STAGES[:index + 1])
    assert build_progress(conn, looked)["next"] is None


def test_a_stage_already_answered_is_not_asked_again(conn, looked):
    asked = {"n": 0}
    monkey = pipeline.opening_spec

    def counted(brief, **kw):
        asked["n"] += 1
        return monkey(brief, **kw)

    pipeline.opening_spec = counted
    try:
        run_stage(conn, looked, "photographs")
        first = run_stage(conn, looked, "direction")
        second = run_stage(conn, looked, "direction")
    finally:
        pipeline.opening_spec = monkey
    assert asked["n"] == 1
    assert first["reused"] is False and second["reused"] is True
    assert first["config"] == second["config"]


def test_a_failure_names_the_stage_rather_than_blanking_the_screen(conn, lead,
                                                                   monkeypatch):
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {})
    with pytest.raises(BuildFailed) as raised:
        run_stage(conn, lead, "photographs")
    assert raised.value.stage == "photographs"
    assert "described" in raised.value.reason


def test_a_retry_reruns_only_the_stage_that_failed(conn, looked, monkeypatch):
    """The whole point. A timeout in the page stage must not re-ask vision or
    the design call."""
    run_stage(conn, looked, "photographs")
    run_stage(conn, looked, "direction")

    boom = {"first": True}
    real = pipeline._build_opening

    def flaky(*args, **kw):
        if boom["first"]:
            boom["first"] = False
            raise RuntimeError("the renderer fell over")
        return real(*args, **kw)

    monkeypatch.setattr(pipeline, "_build_opening", flaky)
    with pytest.raises(BuildFailed) as raised:
        run_stage(conn, looked, "page")
    assert raised.value.stage == "page"
    # The two stages before it are still answered.
    assert build_progress(conn, looked)["done"] == ["photographs", "direction"]
    assert build_progress(conn, looked)["next"] == "page"

    answer = run_stage(conn, looked, "page")
    assert answer["version"] is not None


def test_a_rejected_page_is_not_remembered_as_finished(conn, looked,
                                                       monkeypatch):
    """A rejection is a result, not an answer to store. Remembering it would
    let a retry believe the page stage finished when no version was written."""
    run_stage(conn, looked, "photographs")
    run_stage(conn, looked, "direction")
    monkeypatch.setattr(pipeline, "unsupported", lambda page, material: ["voted"])
    answer = run_stage(conn, looked, "page")
    assert answer["rejected"] is True
    assert answer["version"] is None
    assert sites.recall_stage(conn, looked, "page") is None
    assert build_progress(conn, looked)["next"] == "page"


def test_a_rejection_still_reaches_the_caller_through_the_stages(conn, looked,
                                                                monkeypatch):
    monkeypatch.setattr(pipeline, "unsupported", lambda page, material: ["voted"])
    result = pipeline.open_site(conn, looked)
    assert result.rejected is True
    assert result.version is None
    assert sites.versions(conn, looked) == []


def test_a_rebuild_asks_again_rather_than_replaying_the_stored_decision(
        conn, looked):
    """A rebuild is a request for a fresh decision. Replaying the stored one
    would make correcting a photo description change nothing."""
    pipeline.open_site(conn, looked)
    assert sites.recall_stage(conn, looked, "direction") is not None
    photos.label(conn, looked, "https://x/1.jpg", "the dining room at night")
    pipeline.rebuild_opening(conn, looked)
    assert sites.recall_stage(conn, looked, "direction") is None


def test_an_unknown_stage_is_refused_by_name(conn, lead):
    with pytest.raises(BuildFailed) as raised:
        run_stage(conn, lead, "colouring-in")
    assert raised.value.stage == "colouring-in"


def test_a_photograph_that_cannot_be_fetched_does_not_block_the_build(
        conn, lead, monkeypatch):
    """A scraped image that 404s, hotlink protection, one too large to send —
    the build must not wait forever on a dead URL. It is recorded as looked-at
    and unusable, and never leads."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: True)
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {
        urls[0]: {"subject": "dish", "quality": 4, "is_hero_candidate": True,
                  "alt_text": "A plate"}})
    answer = run_stage(conn, lead, "photographs")
    assert answer["unreachable"] == answer["photographs"] - 1
    seen = photos.vision_for(conn, lead)
    dead = [v for v in seen.values() if v["subject"] == "unclear"]
    assert dead and all(v["is_hero_candidate"] is False for v in dead)
    assert all("fetch" in v["why_not"] for v in dead)


def test_without_a_key_nothing_is_filled_in_on_its_behalf(conn, lead,
                                                          monkeypatch):
    """Filling every photograph in as "could not fetch" would silently unblock
    a build nobody has looked at, which is what the keyless gate exists for."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {})
    with pytest.raises(BuildFailed):
        run_stage(conn, lead, "photographs")
    assert photos.vision_for(conn, lead) == {}


def test_a_second_build_over_the_same_lead_asks_nothing(conn, looked,
                                                        monkeypatch):
    """The census asserts this over the fixtures; this is the same guarantee at
    unit speed. If either answer is re-asked, tuning the diversity budget over
    a few dozen leads is unaffordable and the loop is unusable."""
    asked = {"vision": 0, "direction": 0}
    real_look, real_open = pipeline.vision.look, pipeline.opening_spec

    def counted_look(urls, names):
        asked["vision"] += 1
        return {url: {"subject": "dish", "quality": 4,
                      "is_hero_candidate": True, "alt_text": "A plate"}
                for url in urls}

    def counted_open(brief, **kw):
        asked["direction"] += 1
        return real_open(brief, **kw)

    monkeypatch.setattr(pipeline.vision, "look", counted_look)
    monkeypatch.setattr(pipeline, "opening_spec", counted_open)
    for stage in STAGES:
        run_stage(conn, looked, stage)
    assert asked == {"vision": 1, "direction": 1}

    for stage in STAGES:
        run_stage(conn, looked, stage)
    assert asked == {"vision": 1, "direction": 1}, "a stage was re-asked"
    monkeypatch.setattr(pipeline.vision, "look", real_look)


def test_a_stored_version_renders_the_same_page_twice(conn, looked):
    """Deterministic replay: the same stored spec gives the same HTML, byte for
    byte. A generated design system is what most easily breaks this, so the
    test lands before Slice B rather than after it."""
    from app.site.render import build_from_spec

    result = pipeline.open_site(conn, looked)
    stored = sites.versions(conn, looked)[0]
    brief = leads.brief_with_overrides(conn, looked)
    spec = pipeline.spec_from_config(stored["spec_json"])
    once = build_from_spec(brief, spec)
    twice = build_from_spec(brief, spec)
    assert once == twice
    assert once == sites.html_for(conn, looked, result.version)
