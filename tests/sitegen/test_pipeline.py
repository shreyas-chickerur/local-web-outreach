"""One iteration end to end: parse, render, gate, store."""

from __future__ import annotations

import pytest

from app.site import pipeline
from app.site.pipeline import IterationResult, iterate
from app.site.understand import apply_answer
from app.store import db, leads, photos, sites

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


# --- reading an instruction with a model --------------------------------- #

def model_says(monkeypatch, payload):
    """Stand in for the whole adapter: these tests are about routing, and the
    transport has its own tests."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: True)
    monkeypatch.setattr(pipeline, "understand",
                        lambda sentence, base, **kw:
                        apply_answer(payload, base))


def test_without_a_key_the_phrase_parser_still_runs(conn, lead, monkeypatch):
    """Offline the tool works with a smaller vocabulary. It does not stop."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    result = iterate(conn, lead, "warm and rustic")
    assert result.read_by == "phrases"
    assert result.version is not None


def test_a_model_failure_falls_back_rather_than_losing_the_instruction(
        conn, lead, monkeypatch):
    monkeypatch.setattr(pipeline.claude, "available", lambda: True)

    def boom(sentence, base, **kw):
        raise pipeline.ClaudeError("unreachable")

    monkeypatch.setattr(pipeline, "understand", boom)
    result = iterate(conn, lead, "warm and rustic")
    assert result.read_by == "phrases"
    assert result.version is not None


def test_a_defect_report_does_not_restyle_the_page(conn, lead, monkeypatch):
    """The whole point. "The hours look cramped" is a bug report, and the old
    parser answered it by making the hours bigger."""
    first = iterate(conn, lead, "warm and rustic")
    model_says(monkeypatch, {"kind": "defect",
                             "defect": "the hours are cramped",
                             "understood": []})
    result = iterate(conn, lead, "the hours look cramped")
    assert result.kind == "defect"
    assert result.version is None
    assert result.unchanged is True
    assert result.defect == "the hours are cramped"
    assert [row["version"] for row in sites.versions(conn, lead)] == [first.version]


def test_a_request_to_change_the_facts_is_refused_not_rendered(
        conn, lead, monkeypatch):
    """Business facts come from corroborated sources. An instruction is not a
    source."""
    iterate(conn, lead, "warm and rustic")
    model_says(monkeypatch, {"kind": "content",
                             "understood": ["asked to say they are family owned"],
                             "unsupported": ["cannot add a claim the sources "
                                             "do not support"]})
    result = iterate(conn, lead, "say they are family owned since 1994")
    assert result.kind == "content"
    assert result.version is None


def test_what_the_renderer_cannot_do_is_recorded_in_their_words(
        conn, lead, monkeypatch):
    iterate(conn, lead, "warm and rustic")
    model_says(monkeypatch, {"kind": "unsupported", "understood": [],
                             "unsupported": ["cannot change the size of the logo"]})
    result = iterate(conn, lead, "make the logo bigger")
    assert result.kind == "unsupported"
    assert result.unsupported == ["cannot change the size of the logo"]
    assert result.version is None


def test_a_style_answer_from_the_model_builds_a_version(conn, lead, monkeypatch):
    first = iterate(conn, lead, "warm and rustic")
    model_says(monkeypatch, {"kind": "style", "accent": "navy",
                             "understood": ["accented navy"]})
    result = iterate(conn, lead, "could we try something cooler and more coastal")
    assert result.read_by == "claude"
    assert result.version is not None
    assert result.version != first.version
    assert sites.html_for(conn, lead, result.version) != \
        sites.html_for(conn, lead, first.version)


def test_the_content_gate_still_runs_on_a_model_read(conn, lead, monkeypatch):
    """A model in the loop makes the gate more important, not less."""
    model_says(monkeypatch, {"kind": "style", "mood": "night",
                             "understood": ["styled night"]})
    monkeypatch.setattr(pipeline, "unsupported", lambda page, material: ["voted"])
    result = iterate(conn, lead, "make it darker")
    assert result.rejected is True
    assert result.version is None


# --- the opening version ------------------------------------------------- #

def review_every_photo(conn, lead):
    """Stand in for the operator having looked at them.

    Marking one "unclear" is a decision and counts; leaving it untouched is
    not, which is the whole point of the gate.
    """
    from app.site.render import material_from_brief
    material = material_from_brief(leads.brief_with_overrides(conn, lead))
    for url in material.images:
        photos.label(conn, lead, url, "", what="unclear")


def test_the_first_build_waits_for_the_photographs_to_be_looked_at(
        conn, lead, monkeypatch):
    """Where a photograph goes depends on what it shows, and that is the one
    thing this cannot see. It waits rather than guessing."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    result = pipeline.open_site(conn, lead)
    assert result.kind == "needs_labels"
    assert result.version is None
    assert result.unsupported          # the ones still to look at
    assert sites.versions(conn, lead) == []


def test_marking_one_unclear_counts_as_having_looked(conn, lead, monkeypatch):
    """"I cannot tell what this is" is a decision. A blank field is not, and
    without somewhere to record the difference the build cannot know whether
    the operator is finished."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    review_every_photo(conn, lead)
    assert pipeline.open_site(conn, lead).version is not None


def test_a_new_lead_opens_on_a_site_not_on_nothing(conn, lead, monkeypatch):
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    review_every_photo(conn, lead)
    result = pipeline.open_site(conn, lead)
    assert result.version is not None
    assert sites.html_for(conn, lead, result.version)


def test_opening_twice_does_not_build_twice(conn, lead, monkeypatch):
    """The workspace opens on every click. That is not a request to rebuild."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    review_every_photo(conn, lead)
    first = pipeline.open_site(conn, lead)
    again = pipeline.open_site(conn, lead)
    assert again.version == first.version
    assert again.unchanged is True
    assert len(sites.versions(conn, lead)) == 1


def test_the_content_gate_applies_to_the_opening_version(conn, lead, monkeypatch):
    """A first draft that invents something is not a better first impression
    than none."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    review_every_photo(conn, lead)
    monkeypatch.setattr(pipeline, "unsupported", lambda page, material: ["voted"])
    result = pipeline.open_site(conn, lead)
    assert result.rejected is True
    assert result.version is None
    assert sites.versions(conn, lead) == []


def test_an_instruction_builds_on_the_opening_version(conn, lead, monkeypatch):
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    review_every_photo(conn, lead)
    opened = pipeline.open_site(conn, lead)
    nudged = iterate(conn, lead, "make it darker")
    assert nudged.parent_version == opened.version


def test_a_brand_new_lead_needs_no_human_labelling(conn, lead, monkeypatch):
    """Waiting for a person to describe thirty photographs per lead directly
    contradicts opening on something worth showing."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    from app.site.render import material_from_brief
    material = material_from_brief(leads.brief_with_overrides(conn, lead))
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {
        url: {"subject": "dish", "quality": 4, "is_hero_candidate": True,
              "alt_text": "A plate of food"} for url in urls})
    result = pipeline.open_site(conn, lead)
    assert result.kind == "style"
    assert result.version is not None
    assert photos.unreviewed(conn, lead, list(material.images)) == []


def test_the_operator_still_outranks_the_machine(conn, lead):
    """A machine label unblocks the build. It does not overwrite a person, and
    a person's correction is not overwritten by a later look."""
    photos.label(conn, lead, "/photo/1/0", "the corner booth at night")
    assert photos.record_vision(conn, lead, "/photo/1/0",
                                {"subject": "dish", "alt_text": "food"}) is False
    described = photos.described(conn, lead)["/photo/1/0"]
    assert described["description"] == "the corner booth at night"
    assert described["by_machine"] is False


def test_a_machine_label_is_replaceable_and_says_who_wrote_it(conn, lead):
    photos.record_vision(conn, lead, "/photo/1/0",
                         {"subject": "dish", "alt_text": "A plate of food"})
    described = photos.described(conn, lead)["/photo/1/0"]
    assert described["by_machine"] is True
    assert described["description"] == "A plate of food"
    photos.label(conn, lead, "/photo/1/0", "actually the bar")
    after = photos.described(conn, lead)["/photo/1/0"]
    assert after["by_machine"] is False and after["description"] == "actually the bar"


def test_without_a_key_the_labelling_step_still_guards_the_build(
        conn, lead, monkeypatch):
    """Nothing looked, so designing blind around photographs is worse than
    asking. The keyless path keeps the step."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {})
    assert pipeline.open_site(conn, lead).kind == "needs_labels"


def test_a_correction_after_the_first_build_can_reach_the_page(
        conn, lead, monkeypatch):
    """`open_site` is idempotent, so once v1 exists a corrected description
    would otherwise change nothing at all."""
    monkeypatch.setattr(pipeline.claude, "available", lambda: False)
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {
        url: {"subject": "other", "quality": 2, "alt_text": "something"}
        for url in urls})
    first = pipeline.open_site(conn, lead)
    assert first.version is not None
    # Opening again is not a rebuild.
    assert pipeline.open_site(conn, lead).version == first.version

    photos.label(conn, lead, "/photo/1/0", "the dining room at night")
    again = pipeline.rebuild_opening(conn, lead)
    assert again.version is not None
    assert again.version != first.version
    assert again.parent_version == first.version
