"""The UI layer: serialization and routing.

The page is only trustworthy if it shows what the brief actually established,
so these tests pin the two ways that can go wrong — a conflict rendered as
though it were a fact, and a failing lookup blanking the screen.
"""

from __future__ import annotations

import json

import pytest

from app.web import server
from app.web.serialize import brief_to_dict
from app.workbench.brief import Brief
from app.workbench.corroborate import Fact
from app.workbench.types import Confidence

pytestmark = pytest.mark.unit


def _brief(**kw) -> Brief:
    base = {"name": "Test Co", "location": "Frisco, TX",
            "website_url": None, "notes": None}
    return Brief(**{**base, **kw})


def test_a_conflict_carries_its_candidates_not_a_winner():
    """The UI must be able to name each source; a conflict has no single value."""
    conflict = Fact(field="address", value="A | B", confidence=Confidence.CONFLICT,
                    score=0.3, corroborations=2, sources=[],
                    candidates=[{"value": "A", "source_type": "google",
                                 "source_url": "https://g"},
                                {"value": "B", "source_type": "yelp",
                                 "source_url": "https://y"}])
    payload = brief_to_dict(_brief(facts=[conflict]))
    assert payload["facts"][0]["confidence"] == "conflict"
    assert [c["source_type"] for c in payload["facts"][0]["candidates"]] == [
        "google", "yelp"]
    # A conflicting address must not be promoted into the header.
    assert payload["location"] == "Frisco, TX"


def test_an_established_address_becomes_the_header():
    verified = Fact(field="address", value="2770 Main St, Frisco, TX",
                    confidence=Confidence.VERIFIED, score=0.9, corroborations=2,
                    sources=[{"source_type": "google", "source_url": "https://g"}])
    assert brief_to_dict(_brief(facts=[verified]))["location"] == (
        "2770 Main St, Frisco, TX")


def test_blank_query_is_a_message_not_a_traceback():
    assert "error" in server.lookup("   ", None, None)


def test_a_failing_source_does_not_blank_the_page(monkeypatch):
    """A directory being down should read as an error, not an empty screen."""
    def boom(*a, **k):
        raise RuntimeError("yelp timed out")
    monkeypatch.setattr(server, "build_brief", boom)
    result = server.lookup("Hutchins BBQ", None, None)
    assert "yelp timed out" in result["error"]


def test_a_successful_lookup_archives_the_crawl(monkeypatch, tmp_path):
    """The versioned-brief-storage half of "thicken the brief": every real
    crawl through the actual production entry point gets a permanent,
    never-overwritten copy, not just a DB row the next re-crawl will
    replace."""
    from app.store import brief_archive, db

    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "workbench.db")
    monkeypatch.setattr(brief_archive, "ARCHIVE_ROOT", tmp_path / "briefs")
    monkeypatch.setattr(server, "build_brief",
                        lambda *a, **kw: _brief(name="Craftway Kitchen"))
    result = server.lookup("craftwaykitchen.com", None, None)
    assert "error" not in result
    pointer = brief_archive.current("Craftway Kitchen", root=tmp_path / "briefs")
    assert pointer is not None
    assert (tmp_path / "briefs" / pointer["path"].split("/")[-2]).is_dir()


def test_routes(monkeypatch):
    monkeypatch.setattr(server, "lookup", lambda *a: {"name": "Test Co"})
    assert json.loads(json.dumps(server.lookup("x", None, None)))["name"] == "Test Co"
    assert (server._UI).exists()


def test_the_pages_script_parses():
    """An unbalanced paren in the page silently killed every bit of its
    behaviour: no examples, no results, and no console error to find it by.
    The page has no build step, so nothing else would catch it."""
    import shutil
    import subprocess
    import tempfile

    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    html = server._UI.read_text()
    script = html.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as fh:
        fh.write(script)
        path = fh.name
    done = subprocess.run([node, "--check", path], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_every_function_the_page_calls_actually_exists():
    """A bulk edit deleted three functions the renderer calls, and the only
    symptom was a loading message that never went away — the exception was
    invisible because rendering is what replaces it."""
    import re

    page = server._UI.read_text()
    script = page.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    defined = set(re.findall(r"(?:async\s+)?function\s+(\w+)", script))
    defined |= set(re.findall(r"(?:const|let|var)\s+(\w+)\s*=", script))
    # Everything wired to an onclick/onchange in the markup, plus the calls the
    # renderer makes into its own helpers.
    # Every call in a handler, not just the first: the missing one was second
    # in `onsubmit="event.preventDefault();sendInstruction()"`, so a regex that
    # read only the leading name saw `event` and passed.
    called = set()
    for body in re.findall(r'on(?:click|change|submit|blur|keydown)="([^"]*)"', page):
        called |= set(re.findall(r"(?<![.\w])(\w+)\s*\(", body))
    called |= set(re.findall(r"\$\{(\w+)\(", page))
    builtin = {"if", "for", "return", "esc", "String", "Math", "JSON", "alert",
               "parseInt", "parseFloat", "fetch", "event", "scrollTo",
               "encodeURIComponent"}
    missing = sorted(name for name in called - defined - builtin)
    assert not missing, f"called but never defined: {missing}"


def test_rendering_failures_are_shown_rather_than_swallowed():
    """The loading message stays forever if render() throws, so the failure has
    to be caught and said out loud."""
    page = server._UI.read_text()
    assert "function paint(data)" in page
    assert "could not be drawn" in page


def test_the_labeller_and_the_gate_are_fed_by_one_list():
    """Two lists built two ways can disagree, and the failure is the worst
    kind: every photo on screen is labelled and the build still refuses."""
    source = server._UI.read_text()
    assert "material_from_brief(brief).images" in \
        (server.__file__ and open(server.__file__).read())
    # The page starts on the labelling step rather than a workspace that will
    # refuse — the requirement is visible before it is enforced.
    assert 'stage: (!(data.versions || []).length' in source


def test_labelling_saves_as_you_move_rather_than_at_the_end():
    """Losing twenty descriptions to a stray refresh would teach the operator
    never to write anything longer than a word."""
    source = server._UI.read_text()
    for mover in ("stepShot", "goToShot"):
        start = source.index(f"async function {mover}")
        body = source[start:start + 400]
        assert "await saveShot(" in body, mover


def test_workspace_surfaces_what_did_not_reach_the_page(monkeypatch, tmp_path):
    """BRIEF §5, Slice D item 3: the operator sees what of the business's own
    material never reached the page, and why — reading `app.site.census`'s
    `measure()` directly rather than a second implementation of it, so this
    can only drift from the corpus-wide report (`tools/content_census.py`)
    if `workspace()` stops calling it at all."""
    from pathlib import Path

    from app.site.pipeline import STAGES, run_stage
    from app.store import db, leads

    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "workbench.db")
    fixture = json.loads(
        Path("tests/fixtures/briefs/law-rich.json").read_text())
    with db.session() as conn:
        lead_id = leads.save_brief(conn, fixture)
        for stage in STAGES:
            run_stage(conn, lead_id, stage)

    data = server.workspace(lead_id)
    assert data["census"], "law-rich should have at least one dropped field"
    for row in data["census"]:
        assert set(row) == {"field", "reached", "of", "why"}
        assert row["of"] > row["reached"]
    # `fact:hours` drops on every fixture with published hours already
    # scraped — the fallback fact is never consulted once that happens.
    assert "fact:hours" in {row["field"] for row in data["census"]}


def test_no_class_is_styled_by_two_unrelated_rules():
    """The evidence block under each fact reused `.ev`, a name the history
    timeline already owned. The timeline's grid (a 20px rail, then the text)
    was applied to every piece of evidence: the source tag was crushed into
    the rail and the quote printed on top of it, unreadable, on every lead.

    Rules inside a media query are allowed to repeat a class; that is how a
    narrow layout overrides a wide one."""
    import collections
    import re

    page = server._UI.read_text()
    css = "\n".join(re.findall(r"<style>(.*?)</style>", page, re.S))
    css = re.sub(r"@media[^{]*\{((?:[^{}]*\{[^{}]*\})*)\s*\}", "", css)
    count: collections.Counter[str] = collections.Counter()
    for selectors, _body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for selector in selectors.split(","):
            if re.fullmatch(r"\.[\w-]+", selector.strip()):
                count[selector.strip()] += 1
    assert not [s for s, n in count.items() if n > 1]


def test_every_fault_the_address_check_reports_has_its_own_headline():
    """Every fault was headlined "The link on their Google listing is broken".
    Fish Shack's link works; its site simply has no https. Telling an owner
    their working link is broken is the fastest way to lose the room."""
    import re

    from app.workbench.weburl import FAULTS

    page = server._UI.read_text()
    table = re.search(r"const FAULT_HEADLINES = \{(.*?)\};", page, re.S)
    assert table, "the page has no headline per fault"
    named = set(re.findall(r'"([a-z-]+)":', table.group(1)))
    assert set(FAULTS) <= named, sorted(set(FAULTS) - named)


@pytest.mark.skipif(__import__("app.adapters.chrome_cdp", fromlist=["chrome"]).chrome() is None,
                    reason="needs a real Chrome")
def test_opening_the_workbench_never_opens_a_dialog_nobody_asked_for():
    """Opening the workbench with no saved town asked the browser for its
    location and, when that was declined, went straight to a "Which town?"
    prompt. A dialog nobody asked for blocks the page and freezes any browser
    driving it: it is why every automated look at the workbench hung."""
    import json
    import time

    from app.adapters import chrome_cdp

    with chrome_cdp.cdp_session(chrome_cdp.chrome(), "about:blank", 1200, 800, 1.0,
                                timeout=30) as call:
        call("Page.addScriptToEvaluateOnNewDocument", {"source": (
            "window.__dialogs=[];['alert','confirm','prompt'].forEach(k=>"
            "window[k]=(m)=>{window.__dialogs.push(k+': '+m);return null;});")})
        call("Page.navigate", {"url": server._UI.resolve().as_uri()})
        time.sleep(9)  # the geolocation request gives up after eight seconds
        seen = call("Runtime.evaluate", {"expression": "JSON.stringify(window.__dialogs)",
                                         "returnByValue": True})
    assert json.loads(seen["result"]["result"]["value"]) == []


def test_a_version_button_names_the_version_and_nothing_else():
    """Version buttons read "v10←9": the version with an arrow to its parent.
    Shreyas reads the list to pick a version, and the arrow made each one read
    as a transition. The parent belongs in the hover text."""
    import re

    page = server._UI.read_text()
    button = re.search(r"\">v\$\{v\.version\}(.*?)</button>", page, re.S)
    assert button, "the version button markup moved; find it and re-point this test"
    assert "parent_version" not in button.group(1)


def test_the_workbench_serves_the_logo_the_brief_names_after_corrections(tmp_path, monkeypatch):
    """A page asks for /logo/<lead>. It must be the logo the operator settled on,
    not the crawl's first guess, or a correction changes a screen and nothing a
    visitor would see."""
    from app.store import db, leads

    conn = db.connect(tmp_path / "t.db")
    lead = leads.save_brief(conn, {
        "name": "Fish Shack", "location": "Plano, TX", "website_url": "http://fish.test/",
        "facts": [], "published": {"logo": "http://fish.test/wrong.png"},
        "assumptions": [], "open_questions": [], "sources_consulted": []})
    leads.verify(conn, lead, "logo", "http://fish.test/graphics/fslogo2.jpg")
    asked = []
    monkeypatch.setattr(server.logos, "fetch",
                        lambda url: asked.append(url) or (b"\xff\xd8jpeg", "image/jpeg"))
    assert server.logo_for(conn, lead) == (b"\xff\xd8jpeg", "image/jpeg")
    assert asked == ["http://fish.test/graphics/fslogo2.jpg"]
    conn.close()


def test_a_sentence_on_a_designed_page_goes_to_an_edit_and_the_reply_comes_back(
        tmp_path, monkeypatch):
    """The chat box only understood pages the old renderer built, so every
    version of Fish Shack from 5 on could not be edited from the workbench.
    A page with no renderer spec now goes to an edit run, and the reply is in
    the thread the screen redraws, with what it cost."""
    from app.store import db, leads, sites

    monkeypatch.setattr(server.db, "DB_PATH", tmp_path / "t.db", raising=False)
    conn = db.connect(tmp_path / "t.db")
    lead = leads.save_brief(conn, {
        "name": "Fish Shack", "location": "Plano, TX", "website_url": "http://fish.test/",
        "facts": [], "published": {}, "assumptions": [], "open_questions": [],
        "sources_consulted": []})
    sites.save(conn, lead, "<p>Fish Shack</p>", spec="")
    conn.close()
    monkeypatch.setattr(server.db, "session", lambda: _session(tmp_path / "t.db"))
    asked = {}

    def fake_edit(conn, lead_id, sentence, parent_version=None):
        asked.update(sentence=sentence, parent=parent_version)
        version = sites.save(conn, lead_id, "<p>Fish Shack!</p>", spec="",
                             parent_version=parent_version)
        return {"version": version, "cost_usd": 0.07, "reply": "Added an exclamation mark.",
                "why": "", "flags": []}

    monkeypatch.setattr(server.bridge, "edit", fake_edit)
    payload = server.iteration(lead, "make it louder", 1)
    assert asked == {"sentence": "make it louder", "parent": 1}
    assert payload["version"] == 2 and not payload["rejected"]
    assert "Added an exclamation mark." in payload["thread"][-1]["text"]
    assert "$0.07" in payload["thread"][-1]["text"]


def _session(path):
    import contextlib

    from app.store import db

    @contextlib.contextmanager
    def opened():
        conn = db.connect(path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    return opened()
