"""The design bridge: a lead and a prompt become a new version, with its cost."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from claude_agent_sdk import PermissionResultAllow, ResultMessage

from app.design import bridge
from app.store import db, leads, sites

pytestmark = pytest.mark.unit


def _allowed(options, tool: str, **tool_input) -> bool:
    answer = asyncio.run(options.can_use_tool(tool, tool_input, None))
    return isinstance(answer, PermissionResultAllow)


def test_a_design_run_can_touch_nothing_outside_its_workspace(tmp_path):
    """A design run is an agent with file tools, spending real money. It must
    read the prompt and the photographs and write its page, and nothing else:
    no commands, no network, no file outside its own folder, none of the
    operator's own Claude settings or hooks steering it, and a ceiling."""
    options = bridge.options(tmp_path)
    assert sorted(options.tools) == ["Edit", "Glob", "Read", "Write"]
    # Anything auto-approved would skip the path check below entirely.
    assert options.allowed_tools == []
    assert options.setting_sources == []
    assert options.cwd == str(tmp_path)
    assert (options.model, options.max_budget_usd) == ("claude-opus-5-5", 5.0)
    # The first real run died after reading four photographs: each comes back
    # base64-encoded in one message, and the kit refuses any over 1 MB by default.
    assert options.max_buffer_size >= 16 * 1024 * 1024

    assert _allowed(options, "Write", file_path=str(tmp_path / "index.html"))
    assert _allowed(options, "Read", file_path=str(tmp_path / "photos" / "0.jpg"))
    assert _allowed(options, "Glob", pattern="photos/*.jpg")
    assert not _allowed(options, "Write", file_path=str(tmp_path.parent / "elsewhere.html"))
    assert not _allowed(options, "Write", file_path=str(tmp_path / ".." / "escape.html"))
    assert not _allowed(options, "Read", file_path="/etc/hosts")
    assert not _allowed(options, "Bash", command="ls")
    assert not _allowed(options, "Glob", pattern="*", path="/")
    assert not _allowed(options, "Glob", pattern="../**/*.env")
    assert not _allowed(options, "Glob", pattern="/Users/**/*")


@pytest.fixture()
def lead(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "t.db")
    lead_id = leads.save_brief(conn, {
        "name": "Fish Shack", "location": "Plano, TX", "website_url": "http://fish.test/",
        "facts": [], "published": {}, "assumptions": [], "open_questions": [],
        "sources_consulted": [], "place_photos": ["places/x/photos/a", "places/x/photos/b"]})
    monkeypatch.setattr(bridge.logos, "fetch", lambda url: None)
    asked: list[int] = []
    monkeypatch.setattr(bridge.photos, "fetch", lambda key, name, width=1600:
                        asked.append(width) or f"jpeg of {name}".encode())
    monkeypatch.setattr(bridge, "RUNS", tmp_path / "runs")
    prompt = tmp_path / "v2.md"
    prompt.write_text(f"Use `/photo/{lead_id}/1?w=1600` for the hero.")
    yield conn, lead_id, prompt, asked
    conn.close()


def test_the_workspace_holds_the_prompt_and_the_photographs_as_files(lead):
    """The agent cannot reach the workbench's /photo/ addresses: they only exist
    while the server runs, on this machine. It gets the files, and the prompt
    is rewritten to name them."""
    conn, lead_id, prompt, asked = lead
    work = bridge.prepare(conn, lead_id, prompt)
    assert (work / "photos" / "1.jpg").read_bytes() == b"jpeg of places/x/photos/b"
    assert "photos/1.jpg" in (work / "prompt.md").read_text()
    assert f"/photo/{lead_id}/" not in (work / "prompt.md").read_text()
    # 800 wide is enough to judge a photograph by, and a quarter of the bytes.
    assert set(asked) == {800}


def _result(**kw) -> ResultMessage:
    base = {"subtype": "success", "duration_ms": 1, "duration_api_ms": 1, "is_error": False,
            "num_turns": 7, "session_id": "s", "total_cost_usd": 1.25}
    return ResultMessage(**{**base, **kw})


def test_a_finished_run_becomes_a_version_with_its_cost_and_photographs(lead, monkeypatch):
    """The page the agent wrote names local files. Saved as it is, every
    photograph would be broken in the workbench; and a version with no record
    of its model, prompt and cost cannot be judged or repeated."""
    conn, lead_id, prompt, asked = lead

    async def fake_query(*, prompt, options):
        Path(options.cwd, "index.html").write_text('<img src="photos/1.jpg"><p>Fish</p>')
        yield _result()

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.design(conn, lead_id, prompt)
    assert outcome["version"] == 1 and outcome["cost_usd"] == 1.25
    page = sites.html_for(conn, lead_id, 1)
    assert f'src="/photo/{lead_id}/1?w=1600"' in page
    notes = json.loads(conn.execute(
        "SELECT notes FROM sites WHERE lead_id=? AND version=1", (lead_id,)).fetchone()[0])
    assert notes["model"] == "claude-opus-5-5"
    assert notes["cost_usd"] == 1.25 and notes["turns"] == 7
    assert notes["prompt_file"] == str(prompt) and notes["prompt_sha256"]


def test_a_run_stopped_by_its_ceiling_saves_nothing_and_says_what_it_spent(lead, monkeypatch):
    conn, lead_id, prompt, asked = lead

    async def fake_query(*, prompt, options):
        Path(options.cwd, "index.html").write_text("<p>half a page")
        yield _result(subtype="error_max_budget_usd", is_error=True, total_cost_usd=5.02)

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.design(conn, lead_id, prompt)
    assert outcome["version"] is None and outcome["cost_usd"] == 5.02
    assert "error_max_budget_usd" in outcome["why"]
    assert sites.html_for(conn, lead_id, 1) is None


def test_a_run_that_crashes_says_why_and_saves_nothing(lead, monkeypatch):
    """The first real run crashed before its result arrived, and all that
    reached the operator was a traceback cut off by the terminal."""
    conn, lead_id, prompt, _asked = lead

    async def fake_query(*, prompt, options):
        raise RuntimeError("buffer exceeded")
        yield  # pragma: no cover

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.design(conn, lead_id, prompt)
    assert outcome["version"] is None and "buffer exceeded" in outcome["why"]


def test_the_logo_goes_in_as_a_file_and_comes_out_as_the_workbench_address(lead, monkeypatch):
    """No generated page carried the business's logo, top-left or in the tab.
    The agent gets the logo as a file and is told where it goes; the page it
    writes names the file, which becomes /logo/<lead> in the workbench."""
    conn, lead_id, prompt, _asked = lead
    leads.verify(conn, lead_id, "logo", "http://fish.test/graphics/fslogo2.jpg")
    monkeypatch.setattr(bridge.logos, "fetch", lambda url: (b"\xff\xd8logo", "image/jpeg"))
    seen = {}

    async def fake_query(*, prompt, options):
        seen["logo"] = Path(options.cwd, "logo.jpg").read_bytes()
        seen["told"] = prompt
        Path(options.cwd, "index.html").write_text(
            '<link rel="icon" href="logo.jpg"><img src="logo.jpg" alt="Fish Shack">')
        yield _result()

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.design(conn, lead_id, prompt)
    assert seen["logo"] == b"\xff\xd8logo" and "logo.jpg" in seen["told"]
    page = sites.html_for(conn, lead_id, outcome["version"])
    assert page.count(f"/logo/{lead_id}") == 2 and "logo.jpg" not in page
    assert outcome["flags"] == []


def test_a_run_with_no_logo_is_flagged_and_told_not_to_invent_one(lead, monkeypatch):
    """Shreyas, 23 September: with no usable logo, flag it and wait for him."""
    conn, lead_id, prompt, _asked = lead
    told = {}

    async def fake_query(*, prompt, options):
        told["text"] = prompt
        Path(options.cwd, "index.html").write_text("<p>Fish Shack</p>")
        yield _result()

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.design(conn, lead_id, prompt)
    assert "no logo" in told["text"].lower() and "invent" in told["text"].lower()
    assert any("logo" in f.lower() for f in outcome["flags"])


# ------------------------------ editing in conversation ------------------------------ #
def test_an_edit_changes_the_current_page_and_saves_it_with_its_parent(lead, monkeypatch):
    """Shreyas wants to say "make the menu tabs bigger" on the workbench and see
    the new version, without asking anyone to open a session. The edit works on
    the page as it stands, with the photographs and logo as files, and the
    saved version names them by the workbench's addresses again."""
    conn, lead_id, prompt, _asked = lead
    leads.verify(conn, lead_id, "logo", "http://fish.test/logo.jpg")
    monkeypatch.setattr(bridge.logos, "fetch", lambda url: (b"\xff\xd8logo", "image/jpeg"))
    sites.save(conn, lead_id, f'<img src="/logo/{lead_id}"><img src="/photo/{lead_id}/1?w=1600">'
                              '<nav class="tabs">Menu</nav>', spec="")
    seen = {}

    async def fake_query(*, prompt, options):
        page = Path(options.cwd, "index.html")
        seen["before"] = page.read_text()
        seen["told"] = prompt
        seen["ceiling"] = options.max_budget_usd
        page.write_text(seen["before"].replace('class="tabs"', 'class="tabs big"'))
        yield _result(result="Made the menu tabs larger.", total_cost_usd=0.08)

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.edit(conn, lead_id, "make the menu tabs bigger", parent_version=1)
    assert 'src="logo.jpg"' in seen["before"] and 'src="photos/1.jpg"' in seen["before"]
    assert "make the menu tabs bigger" in seen["told"] and seen["ceiling"] == 1.0
    assert outcome["version"] == 2 and outcome["reply"] == "Made the menu tabs larger."
    page = sites.html_for(conn, lead_id, 2)
    assert 'class="tabs big"' in page and f"/logo/{lead_id}" in page
    assert f"/photo/{lead_id}/1?w=1600" in page
    parent = next(v for v in sites.versions(conn, lead_id) if v["version"] == 2)["parent_version"]
    assert parent == 1


def test_an_edit_that_changes_nothing_saves_nothing_and_says_why(lead, monkeypatch):
    """Asked for a fact the brief does not hold, the edit must leave the page
    alone and say so; a new version identical to its parent is noise."""
    conn, lead_id, prompt, _asked = lead
    sites.save(conn, lead_id, "<p>Fish Shack</p>", spec="")

    async def fake_query(*, prompt, options):
        yield _result(result="The brief has no brunch hours, so I changed nothing.",
                      total_cost_usd=0.03)

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.edit(conn, lead_id, "add our brunch hours", parent_version=1)
    assert outcome["version"] is None and "brunch" in outcome["reply"]
    assert len(sites.versions(conn, lead_id)) == 1
