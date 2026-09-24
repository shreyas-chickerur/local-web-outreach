"""The design bridge: a lead and a design prompt become a new version of its site.

Until this existed, every version of The Heritage Table and Fish Shack was
written by hand in a separate session and loaded into the database by hand. Here
one run of the Agent Software Development Kit does it, in a folder of its
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
import json
import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from app.adapters import logos, photos
from app.core.config import design_model, google_places_api_key
from app.store import brief_archive, leads, sites

# Shreyas's decisions, 23 September 2026.
CEILING_USD = 5.0
EDIT_CEILING_USD = 1.0
MAX_TURNS = 40
TOOLS = ["Read", "Write", "Edit", "Glob"]
RUNS = Path("runs")

_INSTRUCTION = """Read prompt.md in this folder and do what it asks.

The photographs it names are files in photos/ (photos/0.jpg, photos/1.jpg, ...).
Look at them before you design. Reference each by that relative path.

{logo}

Write the finished page to index.html in this folder: one self-contained HTML
file, its CSS inline, fonts from Google Fonts allowed. When index.html is
complete, stop."""

_WITH_LOGO = ("The business's own logo is {name}. Look at it. Put it top-left in the "
              "page's header, and use it as the tab icon: "
              '<link rel="icon" href="{name}">. Reference it by that relative path.')
# Shreyas, 23 September 2026: with no usable logo, flag it and wait for him.
_NO_LOGO = ("There is no logo file: none was found on their site. Do not draw, "
            "invent or imitate a logo, and add no tab icon.")
_EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
               "image/webp": "webp"}


def _logo_file(folder: Path) -> str | None:
    return next((f.name for f in sorted(folder.glob("logo.*"))), None)


def _inside(folder: Path, path: str) -> bool:
    target = Path(path) if Path(path).is_absolute() else folder / path
    return target.resolve().is_relative_to(folder.resolve())


def options(folder: Path, ceiling: float = CEILING_USD) -> ClaudeAgentOptions:
    """The one configuration every design run uses."""
    model = design_model()
    if not model:
        # Left to the kit, an unset model silently becomes whatever its default
        # is that month, billed at that model's price.
        raise RuntimeError("DESIGN_MODEL is not set in .env; a design run needs one")

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
        # Not the operator's own coding-assistant settings: their hooks and plugins would
        # steer a design run the way they steer a coding session.
        setting_sources=[],
        cwd=str(folder), model=model, max_budget_usd=ceiling, max_turns=MAX_TURNS,
        # Every photograph the agent reads comes back base64-encoded in one
        # message, and the kit refuses any over 1 MB by default: the first real
        # run died after its fourth photograph.
        max_buffer_size=32 * 1024 * 1024)


def _workspace(conn: sqlite3.Connection, lead_id: int) -> tuple[Path, dict]:
    """A fresh folder holding the lead's photographs and logo as files."""
    # With corrections: a logo or photograph Shreyas corrected must be the one
    # the design sees. This read the stored crawl and would never have seen it.
    brief = leads.brief_with_overrides(conn, lead_id)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    folder = RUNS / brief_archive._slug(str(brief["name"])) / stamp
    (folder / "photos").mkdir(parents=True)
    for n, name in enumerate(brief.get("place_photos") or []):
        # 800 wide is enough to judge a photograph by, a quarter of the bytes,
        # and cheaper for the model to look at. The page still asks the
        # workbench for 1600.
        data = photos.fetch(google_places_api_key() or "", name, width=800)
        if data:
            (folder / "photos" / f"{n}.jpg").write_bytes(data)
    logo_url = (brief.get("published") or {}).get("logo")
    logo = logos.fetch(str(logo_url)) if logo_url else None
    if logo and logo[1] in _EXTENSIONS:
        (folder / f"logo.{_EXTENSIONS[logo[1]]}").write_bytes(logo[0])
    return folder, brief


def _to_files(html: str, lead_id: int, folder: Path) -> str:
    """The workbench's addresses as the files the agent can open."""
    html = re.sub(rf"/photo/{lead_id}/(\d+)(?:\?w=\d+)?", r"photos/\1.jpg", html)
    logo = _logo_file(folder)
    return html.replace(f"/logo/{lead_id}", logo) if logo else html


def _to_addresses(html: str, lead_id: int) -> str:
    """The files named in a finished page as the workbench's addresses."""
    html = re.sub(r"photos/(\d+)\.jpg", rf"/photo/{lead_id}/\1?w=1600", html)
    return re.sub(r"\blogo\.(?:png|jpg|gif|webp)\b", f"/logo/{lead_id}", html)


def prepare(conn: sqlite3.Connection, lead_id: int, prompt_path: Path) -> Path:
    """A fresh folder with the prompt, the photographs and the logo as files.

    The prompt names photographs by the workbench's `/photo/<lead>/<n>` address,
    which exists only while the server runs on this machine. The agent gets the
    files instead, from the cache the workbench already paid for.
    """
    folder, _brief = _workspace(conn, lead_id)
    text = re.sub(rf"/photo/{lead_id}/(\d+)(?:\?w=\d+)?", r"photos/\1.jpg",
                  prompt_path.read_text())
    (folder / "prompt.md").write_text(text)
    return folder


def say_step(block: ToolUseBlock | TextBlock) -> str:
    """One step of a run in words a person watching the clock can follow.

    A design run is minutes of silence otherwise: the screen could say only
    that it was running, never what it was doing.
    """
    if isinstance(block, TextBlock):
        first = block.text.strip().split("\n")[0]
        return first[:140] + ("…" if len(first) > 140 else "")
    target = str(block.input.get("file_path") or block.input.get("path")
                 or block.input.get("pattern") or "")
    name = Path(target).name
    if block.name == "Read":
        if name.endswith(".jpg"):
            return f"looking at photograph {name.split('.')[0]}"
        if name == "prompt.md":
            return "reading the brief and the playbook"
        if name.startswith("logo"):
            return "looking at the logo"
        return f"reading {name}"
    if block.name == "Write":
        return f"writing {name}" if name != "index.html" else "writing the page"
    if block.name == "Edit":
        return f"revising {name}" if name != "index.html" else "revising the page"
    if block.name == "Glob":
        return "listing the files it was given"
    return block.name


async def _run(folder: Path, told: str | None = None, ceiling: float = CEILING_USD,
               on_step: Callable[[str], None] | None = None,
               ) -> tuple[ResultMessage | None, str]:
    """The run's result, if one arrived, and the error that ended it, if any.

    A crash before the result used to surface only as a traceback, cut off by
    the terminal, with no word of what went wrong.
    """
    result, error = None, ""
    try:
        logo = _logo_file(folder)
        told = told or _INSTRUCTION.format(
            logo=_WITH_LOGO.format(name=logo) if logo else _NO_LOGO)
        async for message in query(prompt=told, options=options(folder, ceiling)):
            if isinstance(message, ResultMessage):
                result = message
            elif on_step and isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock | TextBlock):
                        on_step(say_step(block))
    except Exception as exc:  # noqa: BLE001 — a failed run still reports what it spent
        error = f"{type(exc).__name__}: {exc}"
    return result, error


def design(conn: sqlite3.Connection, lead_id: int, prompt_path: Path,
           on_step: Callable[[str], None] | None = None) -> dict:
    """Run one design and save it as a new version, or say why not."""
    folder = prepare(conn, lead_id, prompt_path)
    result, error = asyncio.run(_run(folder, on_step=on_step))
    flags = [] if _logo_file(folder) else [
        "No logo found for this business. Correct the Logo field on the workbench "
        "with its address, then run the design again."]
    cost = (result.total_cost_usd or 0.0) if result else 0.0
    page = folder / "index.html"
    if result is None or result.is_error or not page.exists():
        why = result.subtype if result else (error or "the run produced no result")
        return {"version": None, "cost_usd": cost, "folder": str(folder),
                "why": f"{why}; nothing was saved", "flags": flags}
    html = _to_addresses(page.read_text(), lead_id)
    prompt_text = prompt_path.read_text()
    brief = leads.load_brief(conn, lead_id)
    current = brief_archive.current(str(brief["name"])) or {}
    previous = sites.versions(conn, lead_id)
    version = sites.save(conn, lead_id, html, spec="", actor="design-run", notes={
        "generator": "agent design run (app/design/bridge.py)",
        "model": design_model(), "cost_usd": cost, "turns": result.num_turns,
        "ended": result.subtype, "run_folder": str(folder),
        "prompt_file": str(prompt_path),
        "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest()[:16],
        "brief_file": current.get("path", ""), "brief_hash": current.get("hash", ""),
        "constraints": "none applied at generation; claim inventory runs at the final gate",
    }, parent_version=max((v["version"] for v in previous), default=None))
    return {"version": version, "cost_usd": cost, "folder": str(folder), "why": "",
            "flags": flags}



_EDIT = """index.html in this folder is the current page of a website proposal for
{name}. Make exactly this change and nothing else:

    {sentence}

Keep everything the request does not touch identical. The photographs are in
photos/ and the logo, if there is one, is the logo file here; use them by those
relative paths. Facts (names, dishes, prices, hours, addresses, phone numbers,
reviews) come only from brief.json: never add or alter one. If the change needs a
fact brief.json does not hold, leave the page as it is and say so. Any words
you write are the business speaking on its own site: never quote it back to itself
or say where a fact came from, and no stock phrases. A dish on the menu in
brief.json is named exactly as the menu names it; name a dish from a photograph only
when it is unmistakable, and never more specifically than the photograph shows.

When you are done, reply in one or two plain sentences saying what you changed."""


def edit(conn: sqlite3.Connection, lead_id: int, sentence: str,
         parent_version: int | None = None) -> dict:
    """One change to the page as it stands, said in a sentence, as a new version.

    The chat box understood only pages the old renderer built, so Fish Shack's
    designed versions could not be edited from the workbench at all. This works
    on the page itself: the same confined agent, a $1 ceiling (Shreyas, 23
    September 2026), and a reply saying what it changed.
    """
    versions = sites.versions(conn, lead_id)
    parent = parent_version or max(v["version"] for v in versions)
    folder, brief = _workspace(conn, lead_id)
    before = _to_files(sites.html_for(conn, lead_id, parent) or "", lead_id, folder)
    (folder / "index.html").write_text(before)
    facts = {k: brief.get(k) for k in ("name", "location", "trade", "facts", "published",
                                       "ratings", "testimonials")}
    # The text of every page the crawl read, the menu among them. Leaving these
    # out, an edit asked to name Yama's dishes from its menu said there was none.
    facts["pages"] = [p for p in brief.get("pages") or [] if p.get("read")]
    (folder / "brief.json").write_text(json.dumps(facts, indent=1, default=str))
    told = _EDIT.format(name=brief.get("name", "the business"), sentence=sentence.strip())
    result, error = asyncio.run(_run(folder, told, EDIT_CEILING_USD))
    cost = (result.total_cost_usd or 0.0) if result else 0.0
    reply = (result.result or "").strip() if result else ""
    after = (folder / "index.html").read_text()
    if result is None or result.is_error:
        why = result.subtype if result else (error or "the run produced no result")
        return {"version": None, "cost_usd": cost, "reply": reply or f"The edit failed: {why}.",
                "why": why, "flags": []}
    if after == before:
        return {"version": None, "cost_usd": cost, "reply": reply or "Nothing changed.",
                "why": "unchanged", "flags": []}
    version = sites.save(conn, lead_id, _to_addresses(after, lead_id), spec="",
                         actor="chat-edit", parent_version=parent, notes={
        "generator": "agent edit (app/design/bridge.py)", "model": design_model(),
        "instruction": sentence.strip(), "reply": reply, "cost_usd": cost,
        "turns": result.num_turns, "ended": result.subtype, "run_folder": str(folder)})
    return {"version": version, "cost_usd": cost, "reply": reply, "why": "", "flags": []}

if __name__ == "__main__":
    import sys

    from app.store import db

    lead_arg, prompt_arg = int(sys.argv[1]), Path(sys.argv[2])
    with db.session() as connection:
        outcome = design(connection, lead_arg, prompt_arg)
    spent = f"${outcome['cost_usd']:.2f} (the kit's estimate)"
    for flag in outcome["flags"]:
        print(f"FLAG: {flag}")
    if outcome["version"]:
        print(f"saved as version {outcome['version']} of lead {lead_arg}, {spent}: "
              f"http://127.0.0.1:8099/site/{lead_arg}/{outcome['version']}")
    else:
        print(f"no version saved, {spent}: {outcome['why']} (run in {outcome['folder']})")
        sys.exit(1)
