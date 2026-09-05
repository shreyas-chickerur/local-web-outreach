"""One iteration end to end: parse, render, gate, store."""

from __future__ import annotations

import pytest

from app.site import pipeline
from app.site.pipeline import IterationResult, iterate
from app.store import db, leads, sites

pytestmark = pytest.mark.unit

BRIEF = {
    "name": "The Heritage Table", "location": "Frisco, TX",
    "website_url": "https://example.com",
    "facts": [{"field": "phone", "value": "(469) 664-0100",
               "confidence": "verified"}],
    "published": {"tagline": "A neighbourhood restaurant.",
                  "services": ["Dinner", "Brunch", "Catering", "Private hire"],
                  "products": [], "menu_items": [], "hours": [],
                  "photos": [f"https://x/{n}.jpg" for n in range(6)],
                  "socials": [], "emails": [], "about": None},
    "ratings": [], "open_questions": [], "assumptions": [],
    "sources_consulted": [], "chain_signals": [],
}


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(tmp_path / "t.db")
    yield connection
    connection.close()


@pytest.fixture()
def lead(conn):
    return leads.save_brief(conn, BRIEF)


# ------------------------------------------------------------ happy path -- #
def test_an_instruction_produces_a_new_version(conn, lead):
    result = iterate(conn, lead, "warm and rustic, lead with the gallery")
    assert isinstance(result, IterationResult)
    assert result.version == 1
    assert result.rejected is False
    assert result.url == f"/site/{lead}/1"
    assert result.spec["mood"] == "warm"
    assert "led with the gallery" in result.understood


def test_each_iteration_carries_the_last_configuration_forward(conn, lead):
    iterate(conn, lead, "warm and rustic, lead with the gallery")
    second = iterate(conn, lead, "actually make it darker")
    assert second.version == 2
    assert second.spec["mood"] == "night"
    assert second.spec["lead_with"] == "gallery"     # not restated, not lost


def test_ignored_words_reach_the_result_not_just_the_notes(conn, lead):
    result = iterate(conn, lead, "make it like a surf shack with hammocks")
    assert "hammocks" in result.ignored_tokens
    assert "hammocks" in result.as_dict()["ignored_tokens"]


def test_a_contradiction_is_reported_alongside_the_version(conn, lead):
    result = iterate(conn, lead, "make it warm but clean")
    assert result.version == 1                      # it still built
    assert result.contradictions                    # and it said what it saw


def test_dropping_a_section_removes_it_from_the_page(conn, lead):
    iterate(conn, lead, "warm")
    result = iterate(conn, lead, "remove the gallery")
    html = sites.html_for(conn, lead, result.version)
    assert 'id="gallery"' not in html
    assert 'id="services"' in html                  # the rest is untouched


# --------------------------------------------------------- the gatekeeper - #
def test_a_page_that_asserts_something_unsupported_is_refused(conn, lead,
                                                              monkeypatch):
    """The gate runs after every other decision, so nothing downstream of the
    parser can slip past it."""
    monkeypatch.setattr(pipeline, "unsupported",
                        lambda page, material: ["since 1994", "award-winning"])
    result = iterate(conn, lead, "warm and rustic")

    assert result.rejected is True
    assert result.version is None and result.url is None
    assert result.findings == ["since 1994", "award-winning"]


def test_a_refusal_writes_no_version_and_leaves_the_last_one_live(conn, lead,
                                                                  monkeypatch):
    good = iterate(conn, lead, "warm and rustic")
    monkeypatch.setattr(pipeline, "unsupported", lambda page, material: ["voted"])
    iterate(conn, lead, "make it bold")

    assert [v["version"] for v in sites.versions(conn, lead)] == [good.version]
    assert sites.html_for(conn, lead) == sites.html_for(conn, lead, good.version)


def test_a_refusal_is_recorded_on_the_trail(conn, lead, monkeypatch):
    """An instruction that produced unsafe output is the most interesting thing
    that happened; discarding it silently would hide it."""
    monkeypatch.setattr(pipeline, "unsupported", lambda page, material: ["voted"])
    iterate(conn, lead, "say we were voted the best")

    entry = leads.events(conn, lead)[0]
    assert entry["kind"] == "site_rejected"
    assert "voted" in entry["new_value"]
    assert entry["note"] == "say we were voted the best"
    assert entry["actor"]


# ------------------------------------------------------------- lineage --- #
def test_a_normal_iteration_parents_the_previous_version(conn, lead):
    first = iterate(conn, lead, "warm")
    second = iterate(conn, lead, "make it bolder")
    assert second.parent_version == first.version


def test_forking_from_an_older_version_still_allocates_the_next_number(conn,
                                                                       lead):
    """Version is a monotonic counter; parent is a pointer. Forking from v3
    while v7 exists must give v8 whose parent is 3 — never a second v4."""
    for sentence in ("warm", "bolder", "darker", "cleaner", "upscale",
                     "industrial", "rustic"):
        iterate(conn, lead, sentence)
    assert [v["version"] for v in sites.versions(conn, lead)][0] == 7

    forked = iterate(conn, lead, "lead with the gallery", parent_version=3)
    assert forked.version == 8
    assert forked.parent_version == 3


def test_every_parent_points_at_a_version_that_exists(conn, lead):
    for sentence in ("warm", "bolder", "darker"):
        iterate(conn, lead, sentence)
    iterate(conn, lead, "cleaner", parent_version=1)

    rows = sites.versions(conn, lead)
    numbers = {row["version"] for row in rows}
    for row in rows:
        parent = row["parent_version"]
        assert parent is None or parent in numbers


def test_nothing_is_its_own_parent(conn, lead):
    for sentence in ("warm", "bolder", "darker"):
        iterate(conn, lead, sentence)
    for row in sites.versions(conn, lead):
        assert row["parent_version"] != row["version"]


def test_an_older_version_is_untouched_by_a_fork(conn, lead):
    original = iterate(conn, lead, "warm and rustic")
    before = sites.html_for(conn, lead, original.version)
    iterate(conn, lead, "make it industrial", parent_version=original.version)
    assert sites.html_for(conn, lead, original.version) == before


def test_versions_never_collide_under_repeated_writes(conn, lead):
    """The version is allocated inside the INSERT rather than read first and
    written after, which is what stops two writers claiming the same number."""
    # Each instruction has to produce a genuinely different page: an iteration
    # that renders the page it started from writes no version, by design.
    for colour in ("blue", "navy", "teal", "forest", "olive", "gold",
                   "mustard", "crimson", "plum", "indigo", "rose", "charcoal"):
        iterate(conn, lead, f"more {colour}")
    numbers = [row["version"] for row in sites.versions(conn, lead)]
    assert numbers == sorted(set(numbers), reverse=True)
    assert len(numbers) == 12


def test_the_stored_configuration_is_what_produced_the_page(conn, lead):
    """Replayability: a version has to be able to explain itself later."""
    result = iterate(conn, lead, "warm and rustic, lead with the gallery")
    row = sites.versions(conn, lead)[0]
    assert row["spec_json"]["mood"] == "warm"
    assert row["spec_json"]["lead_with"] == "gallery"
    assert row["spec"] == "warm and rustic, lead with the gallery"
    assert row["spec_json"] == result.spec


# ------------------------------------------------------- true branching --- #
def test_a_branch_inherits_the_version_it_forked_from(conn, lead):
    """Going back to v1 and changing the mood must inherit v1's ordering and
    call to action — not whatever the newest version happened to be doing."""
    first = iterate(conn, lead, "warm, lead with the gallery, book a table")
    iterate(conn, lead, "make it industrial")
    iterate(conn, lead, "remove the gallery and lead with the menu")

    branched = iterate(conn, lead, "make it darker", parent_version=first.version)
    assert branched.spec["lead_with"] == "gallery"       # from v1, not v3
    assert branched.spec["suppress"] == []               # v3 dropped it; v1 did not
    assert branched.spec["cta"]["kind"] == "book"
    assert branched.spec["mood"] == "night"              # the only change


def test_without_a_parent_an_iteration_still_follows_the_newest(conn, lead):
    iterate(conn, lead, "warm, lead with the gallery")
    iterate(conn, lead, "remove the gallery")
    latest = iterate(conn, lead, "make it bolder")
    assert latest.spec["suppress"] == ["gallery"]        # inherited from v2
    assert latest.parent_version == 2


def test_two_branches_off_one_parent_do_not_contaminate_each_other(conn, lead):
    root = iterate(conn, lead, "warm, lead with the gallery")
    left = iterate(conn, lead, "remove the reviews", parent_version=root.version)
    right = iterate(conn, lead, "make it industrial", parent_version=root.version)

    assert left.parent_version == right.parent_version == root.version
    assert left.spec["suppress"] == ["reviews"]
    assert right.spec["suppress"] == []                  # the other branch's edit
    assert right.spec["mood"] == "industrial"
    assert left.spec["mood"] == "warm"


def test_branching_from_a_version_that_does_not_exist_is_refused(conn, lead):
    iterate(conn, lead, "warm")
    with pytest.raises(ValueError, match="no such version"):
        iterate(conn, lead, "make it bolder", parent_version=99)


def test_an_instruction_that_changes_nothing_writes_no_version(conn, lead):
    """A version should mean something changed. "More blue" used to mint a
    version byte-identical to its parent, leaving the operator staring at an
    unchanged page wearing a fresh number."""
    first = iterate(conn, lead, "warm and rustic")
    again = iterate(conn, lead, "warm and rustic")
    assert again.unchanged is True
    assert again.version is None
    assert [row["version"] for row in sites.versions(conn, lead)] == [first.version]


def test_more_blue_now_changes_the_page(conn, lead):
    warm = iterate(conn, lead, "warm and rustic")
    blue = iterate(conn, lead, "the page should have more blue")
    assert blue.unchanged is False
    assert blue.version is not None
    assert "blue" not in blue.ignored_tokens
    assert sites.html_for(conn, lead, blue.version) != \
        sites.html_for(conn, lead, warm.version)


def test_the_same_words_rebuild_when_the_brief_moved(conn, lead, monkeypatch):
    """The guard compares the rendered page, not the configuration: confirming
    a business's hours legitimately makes the same instruction a new site."""
    first = iterate(conn, lead, "warm and rustic")
    monkeypatch.setattr(pipeline, "build_from_spec",
                        lambda brief, spec: "<html>different</html>")
    again = iterate(conn, lead, "warm and rustic")
    assert again.unchanged is False
    assert again.version != first.version
