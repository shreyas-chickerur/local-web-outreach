"""The design bridge: a lead and a design prompt become a new version of its site.

Until this existed, every version of The Heritage Table and Fish Shack was
written by hand in a Claude session and loaded into the database by hand. Here
one run of the Claude Agent Software Development Kit does it, in a folder of its
own, with a spending ceiling, and the version it produces records the model, the
prompt and what the run cost. The claim checks then read it like any other page.

The agent is given four file tools and nothing else. It cannot run commands or
reach the network, and every file it touches must be inside its own folder:
`can_use_tool` approves each call by path. Nothing is auto-approved, because an
auto-approved tool never reaches that check.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    query,
)

from app.adapters import photos
from app.core.config import google_places_api_key
from app.store import brief_archive, leads, sites

# Shreyas's decisions, 23 September 2026 (SPEC-design-bridge.md).
MODEL = "claude-opus-5-5"
CEILING_USD = 5.0
MAX_TURNS = 40
TOOLS = ["Read", "Write", "Edit", "Glob"]
RUNS = Path("runs")

_INSTRUCTION = """Read prompt.md in this folder and do what it asks.

The photographs it names are files in photos/ (photos/0.jpg, photos/1.jpg, ...).
Look at them before you design. Reference each by that relative path.

Write the finished page to index.html in this folder: one self-contained HTML
file, its CSS inline, fonts from Google Fonts allowed. When index.html is
complete, stop."""


def _inside(folder: Path, path: str) -> bool:
    target = Path(path) if Path(path).is_absolute() else folder / path
    return target.resolve().is_relative_to(folder.resolve())


def options(folder: Path) -> ClaudeAgentOptions:
    """The one configuration every design run uses."""

    async def only_here(tool: str, tool_input: dict[str, Any],
                        _context: Any) -> PermissionResultAllow | PermissionResultDeny:
        path = tool_input.get("file_path") or tool_input.get("path") or ""
        pattern = str(tool_input.get("pattern") or "")
        # A glob pattern can climb out on its own: "../**/*.env".
        climbs = pattern.startswith("/") or ".." in Path(pattern).parts
        if tool in TOOLS and not climbs and (not path or _inside(folder, str(path))):
            return PermissionResultAllow()
        return PermissionResultDeny(message=f"{tool} is limited to {folder}")

    return ClaudeAgentOptions(
        tools=list(TOOLS), allowed_tools=[], can_use_tool=only_here,
        # Not the operator's own Claude settings: their hooks and plugins would
        # steer a design run the way they steer a coding session.
        setting_sources=[],
        cwd=str(folder), model=MODEL, max_budget_usd=CEILING_USD, max_turns=MAX_TURNS)


def prepare(conn: sqlite3.Connection, lead_id: int, prompt_path: Path) -> Path:
    """A fresh folder with the prompt and the lead's photographs as files.

    The prompt names photographs by the workbench's `/photo/<lead>/<n>` address,
    which exists only while the server runs on this machine. The agent gets the
    files instead, from the cache the workbench already paid for.
    """
    brief = leads.load_brief(conn, lead_id)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    folder = RUNS / brief_archive._slug(str(brief["name"])) / stamp
    (folder / "photos").mkdir(parents=True)
    for n, name in enumerate(brief.get("place_photos") or []):
        data = photos.fetch(google_places_api_key() or "", name, width=1600)
        if data:
            (folder / "photos" / f"{n}.jpg").write_bytes(data)
    text = re.sub(rf"/photo/{lead_id}/(\d+)(?:\?w=\d+)?", r"photos/\1.jpg",
                  prompt_path.read_text())
    (folder / "prompt.md").write_text(text)
    return folder


async def _run(folder: Path) -> ResultMessage | None:
    result = None
    try:
        async for message in query(prompt=_INSTRUCTION, options=options(folder)):
            if isinstance(message, ResultMessage):
                result = message
    except Exception:  # noqa: BLE001 — a failed run still reports what it spent
        if result is None:
            raise
    return result


def design(conn: sqlite3.Connection, lead_id: int, prompt_path: Path) -> dict:
    """Run one design and save it as a new version, or say why not."""
    folder = prepare(conn, lead_id, prompt_path)
    result = asyncio.run(_run(folder))
    cost = (result.total_cost_usd or 0.0) if result else 0.0
    page = folder / "index.html"
    if result is None or result.is_error or not page.exists():
        why = result.subtype if result else "the run produced no result"
        return {"version": None, "cost_usd": cost, "folder": str(folder),
                "why": f"{why}; nothing was saved"}
    html = re.sub(r"photos/(\d+)\.jpg", rf"/photo/{lead_id}/\1?w=1600", page.read_text())
    prompt_text = prompt_path.read_text()
    brief = leads.load_brief(conn, lead_id)
    current = brief_archive.current(str(brief["name"])) or {}
    previous = sites.versions(conn, lead_id)
    version = sites.save(conn, lead_id, html, spec="", actor="claude-design", notes={
        "generator": "claude-agent-sdk (app/design/bridge.py)",
        "model": MODEL, "cost_usd": cost, "turns": result.num_turns,
        "ended": result.subtype, "run_folder": str(folder),
        "prompt_file": str(prompt_path),
        "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest()[:16],
        "brief_file": current.get("path", ""), "brief_hash": current.get("hash", ""),
        "constraints": "none applied at generation; claim inventory runs at the final gate",
    }, parent_version=max((v["version"] for v in previous), default=None))
    return {"version": version, "cost_usd": cost, "folder": str(folder), "why": ""}


if __name__ == "__main__":
    import sys

    from app.store import db

    lead_arg, prompt_arg = int(sys.argv[1]), Path(sys.argv[2])
    with db.session() as connection:
        outcome = design(connection, lead_arg, prompt_arg)
    spent = f"${outcome['cost_usd']:.2f} (the kit's estimate)"
    if outcome["version"]:
        print(f"saved as version {outcome['version']} of lead {lead_arg}, {spent}: "
              f"http://127.0.0.1:8099/site/{lead_arg}/{outcome['version']}")
    else:
        print(f"no version saved, {spent}: {outcome['why']} (run in {outcome['folder']})")
        sys.exit(1)
