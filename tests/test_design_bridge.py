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
    monkeypatch.setattr(bridge.photos, "fetch",
                        lambda key, name, width=1600: f"jpeg of {name}".encode())
    monkeypatch.setattr(bridge, "RUNS", tmp_path / "runs")
    prompt = tmp_path / "v2.md"
    prompt.write_text(f"Use `/photo/{lead_id}/1?w=1600` for the hero.")
    yield conn, lead_id, prompt
    conn.close()


def test_the_workspace_holds_the_prompt_and_the_photographs_as_files(lead):
    """The agent cannot reach the workbench's /photo/ addresses: they only exist
    while the server runs, on this machine. It gets the files, and the prompt
    is rewritten to name them."""
    conn, lead_id, prompt = lead
    work = bridge.prepare(conn, lead_id, prompt)
    assert (work / "photos" / "1.jpg").read_bytes() == b"jpeg of places/x/photos/b"
    assert "photos/1.jpg" in (work / "prompt.md").read_text()
    assert f"/photo/{lead_id}/" not in (work / "prompt.md").read_text()


def _result(**kw) -> ResultMessage:
    base = {"subtype": "success", "duration_ms": 1, "duration_api_ms": 1, "is_error": False,
            "num_turns": 7, "session_id": "s", "total_cost_usd": 1.25}
    return ResultMessage(**{**base, **kw})


def test_a_finished_run_becomes_a_version_with_its_cost_and_photographs(lead, monkeypatch):
    """The page the agent wrote names local files. Saved as it is, every
    photograph would be broken in the workbench; and a version with no record
    of its model, prompt and cost cannot be judged or repeated."""
    conn, lead_id, prompt = lead

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
    conn, lead_id, prompt = lead

    async def fake_query(*, prompt, options):
        Path(options.cwd, "index.html").write_text("<p>half a page")
        yield _result(subtype="error_max_budget_usd", is_error=True, total_cost_usd=5.02)

    monkeypatch.setattr(bridge, "query", fake_query)
    outcome = bridge.design(conn, lead_id, prompt)
    assert outcome["version"] is None and outcome["cost_usd"] == 5.02
    assert "error_max_budget_usd" in outcome["why"]
    assert sites.html_for(conn, lead_id, 1) is None
