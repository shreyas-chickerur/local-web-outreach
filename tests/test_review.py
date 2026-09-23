"""The approval stage: what the checks see, and what the record keeps."""

from __future__ import annotations

import json
import sqlite3

import pytest

from app.review import checks
from app.store import reviews

PAGE = """
<html><head><meta name="description" content="A place."></head><body>
<h1>The Heritage Table</h1>
<p>Rich Vana opened The Heritage Table in 2013.</p>
<p>7110 Main Street has been somebody's livelihood for a century.</p>
<p>Open Sunday to Wednesday, 5pm to 9pm.</p>
<a href="#nowhere">gone</a><a href="">empty</a>
<img src="a.jpg">
</body></html>
"""

CAPTURE = """
Rich Vana is the Chef and Owner of The Heritage Table, which opened in 2013.
Sunday - Wednesday: 5pm - 9pm
"""

BRIEF = {"name": "The Heritage Table", "website_url": "http://example.test",
         "facts": [{"field": "phone", "label": "Phone", "value": "(469) 664-0100",
                    "confidence": "verified"},
                   {"field": "address", "label": "Address",
                    "value": "7110 Main St, Frisco, TX 75033",
                    "confidence": "verified"},
                   {"field": "hours", "label": "Hours",
                    "value": "Mon-Wed 5pm-9pm · Thu-Sat 5pm-10pm",
                    "confidence": "verified"}]}


def verdicts(findings, verdict):
    return [f for f in findings if f.verdict == verdict]


def test_a_sentence_the_source_carries_whole_is_corroborated_with_its_words():
    found = checks.inventory(PAGE, BRIEF, CAPTURE)
    hit = [f for f in verdicts(found, "corroborated") if "2013" in f.quote]
    assert hit, "the opening year is stated verbatim in the capture"
    assert "opened in 2013" in hit[0].evidence


def test_a_paraphrase_nobody_wrote_is_not_waved_through():
    """The sentence carries no number and no proper noun but two long words —
    'livelihood' and 'century' — and neither is in the source."""
    found = checks.inventory(PAGE, BRIEF, CAPTURE)
    assert any("livelihood" in f.quote for f in verdicts(found, "unsourced"))


def test_a_missing_verified_fact_is_the_only_hard_verdict():
    found = checks.contradictions(PAGE, BRIEF)
    assert [f.verdict for f in found] == ["contradicted"]
    assert "phone" in found[0].title


def test_every_mechanical_finding_says_where_it_is():
    found = checks.mechanics(PAGE, BRIEF)
    assert found, "the page has plenty wrong with it"
    assert all(f.locator for f in found), "a finding with no locator is a chore"


def test_a_dead_anchor_names_the_link_and_the_id():
    found = [f for f in checks.mechanics(PAGE, BRIEF) if "nowhere" in f.title]
    assert found and 'href="#nowhere"' in found[0].locator


def test_each_photograph_gets_its_own_finding_named_after_the_file():
    found = [f for f in checks.mechanics(PAGE, BRIEF) if "a.jpg" in f.title]
    assert len(found) == 1, "one finding per picture, not one counting them"
    assert "no alt text" in found[0].title
    assert found[0].anchor == 'css:img[src="a.jpg"]', "the pin lands on that picture"


def test_missing_structured_data_is_answered_with_the_brief_own_facts():
    found = [f for f in checks.structured_data(PAGE, BRIEF)][0]
    block = json.loads(found.evidence)
    assert block["@type"] == "Restaurant"
    assert block["telephone"] == "(469) 664-0100", "taken from the verified brief"
    assert found.quote == "(nothing on the page)"


def test_published_structured_data_is_checked_against_the_brief():
    page = ('<script type="application/ld+json">'
            '{"@type":"Restaurant","name":"The Heritage Table",'
            '"telephone":"(555) 000-0000"}</script>')
    found = checks.structured_data(page, BRIEF)
    assert [f.verdict for f in found] == ["contradicted"]
    assert found[0].quote == "(555) 000-0000"
    assert found[0].evidence == "(469) 664-0100"


def test_hours_that_cannot_be_read_are_left_out_rather_than_guessed():
    spec, note = checks._hours_schedule("Mon-Wed 5pm-9pm · by appointment")
    assert len(spec) == 1 and spec[0]["opens"] == "17:00"
    assert "by appointment" in note


def test_entities_and_curly_punctuation_do_not_invent_findings():
    page = "<p>Sun &ndash; Wed 5pm &ndash; 9pm</p>"
    capture = "Sun - Wed 5pm - 9pm"
    assert not verdicts(checks.inventory(page, {}, capture), "unsourced")


# ------------------------------------------------------------------ the record


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    from app.store import db
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "t.db")
    connection = db.connect(tmp_path / "t.db")
    now = "2026-01-01T00:00:00+00:00"
    connection.execute(
        "INSERT INTO leads(id,key,name,location,website_url,status,brief_json,"
        "created_at,updated_at) VALUES(1,'k','X','Y','u','new',?,?,?)",
        (json.dumps(BRIEF), now, now))
    connection.commit()
    yield connection
    connection.close()


def rows(verdict="unsourced"):
    return [{"stage": "claim", "verdict": verdict, "title": "A claim"}]


def test_reopening_a_review_never_regenerates_its_findings(conn):
    first = reviews.open_review(conn, 1, 1, rows(), actor="me")
    reviews.mark(conn, first["findings"][0]["id"], "confirmed", "checked it", actor="me")
    again = reviews.open_review(conn, 1, 1, rows(), actor="me")
    assert len(again["findings"]) == 1
    assert again["findings"][0]["note"] == "checked it", "a note survives a reopen"


def test_a_contradiction_blocks_approval_until_somebody_resolves_it(conn):
    review = reviews.open_review(conn, 1, 1, rows("contradicted"), actor="me")
    with pytest.raises(ValueError, match="contradicted"):
        reviews.decide(conn, review["id"], reviews.APPROVED, "ship", actor="me")
    reviews.mark(conn, review["findings"][0]["id"], "corrected", "fixing", actor="me")
    decided = reviews.decide(conn, review["id"], reviews.APPROVED, "ship", actor="me")
    assert decided["stage"] == reviews.APPROVED


def test_advice_does_not_block_but_is_recorded(conn):
    review = reviews.open_review(conn, 1, 1, rows("unsourced"), actor="me")
    decided = reviews.decide(conn, review["id"], reviews.APPROVED,
                             "shipping over one unsourced line", actor="me")
    assert decided["stage"] == reviews.APPROVED
    assert decided["decision_note"] == "shipping over one unsourced line"


def test_every_decision_lands_in_the_append_only_trail(conn):
    review = reviews.open_review(conn, 1, 1, rows(), actor="me")
    reviews.mark(conn, review["findings"][0]["id"], "dismissed", "not worth it", actor="me")
    reviews.decide(conn, review["id"], reviews.SENT_BACK, "one more pass", actor="me")
    trail = [(r["kind"], r["new_value"]) for r in conn.execute(
        "SELECT kind, new_value FROM events WHERE lead_id=1 ORDER BY id")]
    assert trail == [("review", "opened"), ("finding", "dismissed"),
                     ("review", "sent back")]


def test_a_review_belongs_to_one_version_and_cannot_be_reused(conn):
    reviews.open_review(conn, 1, 1, rows(), actor="me")
    second = reviews.open_review(conn, 1, 2, rows(), actor="me")
    assert second["version"] == 2
    assert reviews.for_version(conn, 1, 1)["id"] != second["id"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO reviews(lead_id,version,opened_at,opened_by)"
                     " VALUES(1,1,'now','me')")


def test_a_number_written_as_a_word_matches_the_figure_in_the_source():
    page = "<p>We cook from fifteen Texas farms.</p>"
    capture = "PARTNERS: 15 Texas farms, named with town and product"
    found = checks.inventory(page, {}, capture)
    assert [f.verdict for f in found] == ["corroborated"]


def test_a_change_of_tense_is_not_a_finding():
    page = "<p>The Gulledge family purchases the property at 7110 Main Street.</p>"
    capture = ("7110 Main Street: the property was originally purchased "
               "by the Gulledge family.")
    assert not [f for f in checks.inventory(page, {}, capture)
                if f.verdict != "corroborated"]


def test_a_menu_line_and_its_tag_on_neighbouring_lines_count_as_one_passage():
    page = "<p>Add house-made jam — 2 · gluten friendly, vegetarian</p>"
    capture = ("Dietary menu: vegetarian, vegan, gluten friendly offerings\n"
               "Milk & Honey Rolls - 7 - order of three. Add house-made jam 2\n"
               "Milk & Honey Rolls (V), jam (GF)(V)")
    assert [f.verdict for f in checks.inventory(page, {}, capture)] == ["corroborated"]


def test_prose_nobody_published_is_wording_to_read_not_a_fact_to_verify():
    page = "<p>7110 Main Street has been somebody's livelihood for a century.</p>"
    found = checks.inventory(page, {}, "7110 Main Street, Frisco")[0]
    assert found.verdict == "wording", (
        "no figure, no name — asking somebody to verify the word 'livelihood' "
        "wastes their afternoon")
    assert "livelihood" in found.title, "the title names the word, not the sentence"
    assert "noth" not in found.title, "a stem is for matching, never for reading"
    assert "nothing to check it against" in found.detail


def test_a_figure_nobody_published_is_a_fact_to_go_and_confirm():
    page = "<p>Serving Frisco since 1987.</p>"
    found = checks.inventory(page, {}, "A restaurant in Frisco.")[0]
    assert found.verdict == "unsourced"
    assert "1987" in found.title
    assert "ask them" in found.detail


def test_the_pointer_current_json_is_followed_to_the_crawl_it_names(tmp_path):
    """`make brief` rewrites current.json as a pointer, not as the brief.

    Read literally it is three keys and no facts, so every claim came back
    "unsourced" while the screen reported a brief had been loaded — the worst
    of both, a confident answer with nothing behind it.
    """
    import json

    from app.review.run import material

    slug = tmp_path / "briefs" / "the-heritage-table"
    slug.mkdir(parents=True)
    crawl = slug / "2026-09-21T20-32-53.585561+00-00.json"
    crawl.write_text(json.dumps({
        "name": "The Heritage Table",
        "website_url": "https://theheritagetable.test/",
        "facts": [{"field": "phone", "value": "(469) 664-0100"}],
    }))
    (slug / "current.json").write_text(json.dumps({
        "path": "briefs/the-heritage-table/2026-09-21T20-32-53.585561+00-00.json",
        "hash": "f04131b0bbdbfe9a",
        "captured_at": "2026-09-21T20:32:53+00:00",
    }))

    brief, _capture, meta = material("The Heritage Table", root=tmp_path)
    assert brief["name"] == "The Heritage Table"
    assert brief["facts"][0]["value"] == "(469) 664-0100"
    assert meta["brief_file"].endswith("2026-09-21T20-32-53.585561+00-00.json")


def test_a_pointer_to_a_crawl_that_is_gone_reports_no_brief(tmp_path):
    import json

    from app.review.run import material

    slug = tmp_path / "briefs" / "acme-roofing"
    slug.mkdir(parents=True)
    (slug / "current.json").write_text(json.dumps(
        {"path": "briefs/acme-roofing/deleted.json", "hash": "x"}))

    brief, _capture, meta = material("Acme Roofing", root=tmp_path)
    assert brief == {}
    assert meta["brief_file"] == ""
    assert meta["brief_hash"] == ""


def test_a_brief_written_straight_into_current_json_still_loads(tmp_path):
    """Older leads have the whole brief in current.json. Both shapes work."""
    import json

    from app.review.run import material

    slug = tmp_path / "briefs" / "acme-roofing"
    slug.mkdir(parents=True)
    (slug / "current.json").write_text(json.dumps(
        {"name": "Acme Roofing", "facts": [{"field": "phone", "value": "1"}]}))

    brief, _capture, meta = material("Acme Roofing", root=tmp_path)
    assert brief["facts"][0]["value"] == "1"
    assert meta["brief_file"].endswith("current.json")


def test_the_checks_judge_the_page_against_your_corrections(tmp_path, monkeypatch):
    """B2: `material` reads the archived crawl, which predates every correction.

    A fact the operator fixed at the front door was still being checked against
    what a directory published months earlier, so their own correction came
    back as a contradiction on the page.
    """
    import app.web.server as server
    from app.store import db, leads

    conn = db.connect(tmp_path / "t.db")
    lead = leads.save_brief(conn, {
        "name": "Acme Roofing", "location": "Frisco, TX",
        "website_url": "https://acme.test/",
        "facts": [{"field": "phone", "value": "(111) 111-1111",
                   "confidence": "verified", "score": 90}],
        "published": {}, "assumptions": [], "open_questions": [],
        "sources_consulted": [],
    })
    leads.verify(conn, lead, "phone", "(222) 222-2222", note="answered the door")

    monkeypatch.setattr(server.review_run, "material",
                        lambda name: ({"name": name, "facts": [
                            {"field": "phone", "value": "(111) 111-1111"}]},
                            "", {"brief_hash": "abc", "capture_hash": ""}))
    brief, _capture, where = server._review_brief(conn, lead, "Acme Roofing")
    phone = next(f for f in brief["facts"] if f["field"] == "phone")
    assert phone["value"] == "(222) 222-2222"
    assert phone["confidence"] == "operator_verified"
    # The provenance record is untouched: the review still belongs to a crawl.
    assert where["brief_hash"] == "abc"
    conn.close()


def test_a_lead_with_no_stored_brief_falls_back_to_the_archive(tmp_path, monkeypatch):
    import app.web.server as server
    from app.store import db

    conn = db.connect(tmp_path / "t.db")
    archived = {"name": "Acme", "facts": [{"field": "phone", "value": "x"}]}
    monkeypatch.setattr(server.review_run, "material",
                        lambda name: (archived, "", {"brief_hash": "abc"}))
    brief, _capture, _where = server._review_brief(conn, 999, "Acme")
    assert brief is archived
    conn.close()


def test_confirming_what_the_sources_said_rebuilds_nothing(tmp_path):
    """A rebuild costs a generation run. Only a real change is worth one."""
    import app.web.server as server
    from app.store import db

    conn = db.connect(tmp_path / "t.db")
    outcome = {"kind": "verified", "was": "x", "value": "x"}
    assert server.rebuild_after(conn, 1, "phone", outcome)["built"] is False
    conn.close()


def test_a_correction_on_a_lead_with_no_version_yet_rebuilds_nothing(tmp_path):
    import app.web.server as server
    from app.store import db, leads

    conn = db.connect(tmp_path / "t.db")
    lead = leads.save_brief(conn, {
        "name": "Acme", "location": None, "website_url": None, "facts": [],
        "published": {}, "assumptions": [], "open_questions": [],
        "sources_consulted": []})
    answer = server.rebuild_after(conn, lead, "phone",
                                  {"kind": "corrected", "was": "x", "value": "y"})
    assert answer["built"] is False
    assert "no version yet" in answer["why"]
    conn.close()


def test_a_failed_rebuild_never_loses_the_correction(tmp_path, monkeypatch):
    import app.web.server as server
    from app.store import db, leads, sites

    conn = db.connect(tmp_path / "t.db")
    lead = leads.save_brief(conn, {
        "name": "Acme", "location": None, "website_url": None, "facts": [],
        "published": {}, "assumptions": [], "open_questions": [],
        "sources_consulted": []})
    sites.save(conn, lead, "<html></html>", spec="", actor="test")

    def explode(*_args, **_kw):
        raise RuntimeError("no model key")

    monkeypatch.setattr(server, "run_iteration", explode)
    answer = server.rebuild_after(conn, lead, "phone",
                                  {"kind": "corrected", "was": "x", "value": "y"})
    assert answer["built"] is False
    assert answer["correction_saved"] is True
    assert "no model key" in answer["why"]
    conn.close()


# --------------------- the checks read the crawl's page text --------------------- #
def _archive(tmp_path, brief: dict) -> None:
    import json

    slug = tmp_path / "briefs" / "fish-shack"
    slug.mkdir(parents=True)
    (slug / "2026-09-22T21-59-02.000000+00-00.json").write_text(json.dumps(brief))
    (slug / "current.json").write_text(json.dumps({
        "path": "briefs/fish-shack/2026-09-22T21-59-02.000000+00-00.json", "hash": "x"}))


_PAGES = [
    {"url": "http://fish.test/", "kind": "page", "read": True, "reason": "",
     "text": "Fantastic Grilled, Boiled, and Fried Seafood\nHOURS: 10:30am to 10:00pm"},
    {"url": "http://fish.test/wine/", "kind": "page", "read": True, "reason": "",
     "text": "Cabernet Sauvignon, Napa Valley 1994"},
    {"url": "http://fish.test/gone.pdf", "kind": "pdf", "read": False,
     "reason": "could not download", "text": ""},
]


def test_the_checks_search_the_crawls_page_text_not_a_hand_made_capture(tmp_path):
    """The claim inventory judged every page against `live-site.md`, a copy made
    by hand on 16 September that nothing kept current, and gave confident
    answers from it. The crawl's own stored text is the only source now."""
    from app.review.run import material

    _archive(tmp_path, {"name": "Fish Shack", "facts": [], "pages": _PAGES})
    stale = tmp_path / "captures" / "fish-shack"
    stale.mkdir(parents=True)
    (stale / "live-site.md").write_text("Merlot, Sonoma 2001")
    _brief, text, meta = material("Fish Shack", root=tmp_path)
    assert "Cabernet Sauvignon, Napa Valley 1994" in text
    assert "Merlot" not in text
    assert meta["capture_hash"] and "live-site" not in meta["capture_file"]


def test_a_page_the_crawl_could_not_read_is_listed_with_its_reason():
    """A claim that could only be backed by a page nobody could read is not the
    same as a claim nobody made. The reviewer is told which page and why."""
    from app.review.run import findings, page_text

    brief = {"name": "Fish Shack", "facts": [], "pages": _PAGES}
    rows = findings("<p>Hello.</p>", brief, page_text(brief))
    unread = [r for r in rows if r["verdict"] == "unmeasured"]
    assert len(unread) == 1
    assert "gone.pdf" in unread[0]["title"] + unread[0]["detail"]
    assert "could not download" in unread[0]["detail"]


def test_a_brief_crawled_before_page_text_was_kept_says_so():
    from app.review.run import findings, page_text

    brief = {"name": "Old Lead", "facts": []}
    rows = findings("<p>Hello.</p>", brief, page_text(brief))
    assert rows[0]["verdict"] == "unmeasured"
    assert "re-crawl" in (rows[0]["title"] + rows[0]["detail"]).lower()


def test_a_corrected_fact_outranks_the_crawl_that_it_replaced():
    """What the operator was told outranks every source. A page still printing
    the number they corrected must come back contradicted, not corroborated by
    the very crawl text the correction replaced."""
    from app.review.run import findings, page_text

    brief = {"name": "Acme", "facts": [{
        "field": "phone", "value": "(222) 222-2222", "confidence": "operator_verified",
        "superseded": "(111) 111-1111", "sources": []}],
        "pages": [{"url": "http://acme.test/", "kind": "page", "read": True, "reason": "",
                   "text": "Call us: (111) 111-1111"}]}
    page = "<p>Call us today at (111) 111-1111.</p>"
    rows = findings(page, brief, page_text(brief))
    contradicted = [r for r in rows if r["verdict"] == "contradicted"]
    assert contradicted and "you were told" in contradicted[0]["detail"]
    assert not [r for r in rows if r["verdict"] == "corroborated" and "111" in r["quote"]]


def test_the_text_searched_comes_from_the_same_brief_the_page_is_judged_against(
        tmp_path, monkeypatch):
    """The facts came from the lead's brief in the database and the text from the
    archived file. When the two were different crawls, a claim was judged
    against one crawl's facts and another crawl's words."""
    import app.web.server as server
    from app.store import db, leads

    conn = db.connect(tmp_path / "t.db")
    lead = leads.save_brief(conn, {
        "name": "Fish Shack", "location": "Plano, TX", "website_url": "http://fish.test/",
        "facts": [{"field": "phone", "value": "(469) 229-0838", "confidence": "verified"}],
        "published": {}, "assumptions": [], "open_questions": [], "sources_consulted": [],
        "pages": [{"url": "http://fish.test/", "kind": "page", "read": True, "reason": "",
                   "text": "Cabernet Sauvignon"}]})
    monkeypatch.setattr(server.review_run, "material", lambda name: (
        {"name": name, "facts": [{"field": "phone", "value": "x"}]}, "Merlot",
        {"brief_hash": "abc", "capture_hash": "old", "capture_file": "archive"}))
    _brief, text, where = server._review_brief(conn, lead, "Fish Shack")
    assert "Cabernet" in text and "Merlot" not in text
    assert where["capture_hash"] != "old"
    conn.close()


def test_a_plural_in_ies_and_a_thousands_comma_are_still_found_in_the_source():
    """Fish Shack's page said "Hushpuppies", "Veggies" and "3,351 Google
    reviews", all of which its own site and the brief carry, and all came back
    unsourced: "hushpuppies" was stemmed to "hushpuppy" and then looked for in
    text that never says that, and "3,351" was looked for in a brief that
    stores 3351. A checker that flags the business's own menu teaches the
    reviewer to stop reading it."""
    from app.review.checks import inventory

    brief = {"ratings": [{"source": "google", "value": 4.5, "reviews": 3351}]}
    text = "12 Hushpuppies 3.95\nVeggies & Rice 5.95\nFISH SHACK SPECIALTIES"
    page = ("<p>Twelve Hushpuppies for the table.</p><p>Veggies &amp; Rice, 5.95.</p>"
            "<p>Fish Shack Specialties, six of them.</p><p>4.5 from 3,351 Google reviews.</p>")
    unsourced = [f.title for f in inventory(page, brief, text) if f.verdict == "unsourced"]
    assert unsourced == []


# ------------------- each claim points at where it was said ------------------- #
_MAPPED_BRIEF = {
    "name": "Fish Shack",
    "facts": [{"field": "phone", "label": "Phone", "value": "(469) 229-0838",
               "confidence": "verified",
               "sources": [{"source_type": "google", "source_url": "https://maps.test/fs"}]}],
    "ratings": [{"source": "google", "value": 4.5, "reviews": 3351,
                 "source_url": "https://maps.test/fs"}],
    "pages": [
        {"url": "http://fish.test/", "kind": "page", "read": True, "reason": "",
         "text": "Welcome to Fish Shack"},
        {"url": "http://fish.test/menu.htm", "kind": "page", "read": True, "reason": "",
         "text": "Salmon 18.95\nRainbow Trout 16.95"},
    ],
}


def test_a_corroborated_claim_links_to_the_page_and_the_words_that_back_it():
    """Every finding carried the same links (the site, and one source per fact),
    so a reviewer checking "Salmon, 18.95" was sent to the homepage to hunt for
    it. The link now opens the page it was read from, at the words."""
    import json

    from app.review.run import findings, page_text

    rows = findings("<p>Salmon, 18.95.</p>", _MAPPED_BRIEF, page_text(_MAPPED_BRIEF))
    salmon = next(r for r in rows if "Salmon" in r["quote"])
    assert salmon["verdict"] == "corroborated"
    first = json.loads(salmon["resources"])[0]
    assert first["url"].startswith("http://fish.test/menu.htm#:~:text=Salmon")


def test_a_claim_backed_by_a_directory_fact_points_at_that_fact():
    """"4.5 from 3,351 Google reviews" came back "assembled": the rating is in
    the brief, not in any page's text, so no single passage carried it. A
    rating or a verified fact is itself something a source said."""
    import json

    from app.review.run import findings, page_text

    rows = findings("<p>4.5 from 3,351 Google reviews.</p><p>Phone (469) 229-0838.</p>",
                    _MAPPED_BRIEF, page_text(_MAPPED_BRIEF))
    rating = next(r for r in rows if "3,351" in r["quote"])
    phone = next(r for r in rows if "229-0838" in r["quote"])
    for row in (rating, phone):
        assert row["verdict"] == "corroborated", row
        assert json.loads(row["resources"])[0]["url"] == "https://maps.test/fs"
