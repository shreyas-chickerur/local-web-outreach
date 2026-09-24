"""One folder per business, on this machine only: everything made for it.

    sites/<slug>/briefs/       every crawl, and current.json pointing at the newest
    sites/<slug>/prompts/      the design prompts, vN.md
    sites/<slug>/versions/     every version of the page, vN.html
    sites/<slug>/master.txt    the version last marked as a good site
    sites/<slug>/proposals/    the self-contained files made for the owner

`sites/` is gitignored and the repository is public: nothing that belongs to a
business goes to GitHub. The database stays the workbench's index of versions,
parents and the master; this is the copy a person can open, back up or move to
another machine. Every version reaches it because every version is saved
through `sites.save`, whichever path made it.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path("sites")


def slug(name: str) -> str:
    """A filesystem-safe folder name for this business."""
    lowered = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return lowered or "unnamed"


def of(name: str, root: Path | None = None) -> Path:
    # Read ROOT here rather than as a default argument, so a test that points
    # it at a temporary folder is obeyed by every caller.
    return (ROOT if root is None else root) / slug(name)


def _name(conn: sqlite3.Connection, lead_id: int) -> str:
    row = conn.execute("SELECT name FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return str(row["name"]) if row else f"lead-{lead_id}"


def write_version(conn: sqlite3.Connection, lead_id: int, version: int, html: str) -> Path:
    path = of(_name(conn, lead_id)) / "versions" / f"v{version}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
    return path


def write_master(conn: sqlite3.Connection, lead_id: int, version: int) -> Path:
    path = of(_name(conn, lead_id)) / "master.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"v{version}\n")
    return path


def fill(conn: sqlite3.Connection) -> list[Path]:
    """Write every stored version and master into the folders. Safe to repeat.

    For the versions saved before the folders existed; everything saved since
    is written as it is made.
    """
    from app.store import leads

    written = [write_version(conn, int(r["lead_id"]), int(r["version"]), str(r["html"] or ""))
               for r in conn.execute("SELECT lead_id, version, html FROM sites")]
    for row in conn.execute("SELECT id FROM leads"):
        master = leads.master_version(conn, int(row["id"]))
        if master is not None:
            written.append(write_master(conn, int(row["id"]), master))
    return written


if __name__ == "__main__":
    from app.store import db

    with db.session() as conn:
        print(f"{len(fill(conn))} files written under {ROOT}/")
