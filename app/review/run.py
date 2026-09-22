"""Assemble a version's findings from the same material the prompt was built
from — the brief, the capture of the business's own site, and the page itself.

Kept apart from `checks` so the checks stay pure functions over text, testable
without a database, and apart from `store.reviews` so the record does not
depend on how a finding was produced.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.review import checks

BRIEFS = Path("briefs")
CAPTURES = Path("captures")


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "unnamed"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def material(name: str, *, root: Path | None = None) -> tuple[dict, str, dict]:
    """The brief and the capture for a business, with their hashes.

    A missing capture is not an error — an early lead may not have one — but
    it is recorded, because a claim check run without the business's own words
    can only ever return "unsourced" and somebody should be told that rather
    than reading a wall of warnings as evidence of fabrication.
    """
    base = root or Path()
    slug = _slug(name)
    brief_path = base / BRIEFS / slug / "current.json"
    capture_path = base / CAPTURES / slug / "live-site.md"

    brief: dict = {}
    if brief_path.exists():
        brief = json.loads(brief_path.read_text())
        # `current.json` is a POINTER — {"path", "hash", "captured_at"} — that
        # `brief_archive.save` rewrites on every crawl. Read literally it is a
        # three-key dictionary with no facts in it, which every check then
        # reports as "unsourced" while the screen says a brief was loaded. So
        # follow it to the archived crawl it names.
        if "facts" not in brief and brief.get("path"):
            pointed_at = base / str(brief["path"])
            if pointed_at.exists():
                brief = json.loads(pointed_at.read_text())
                brief_path = pointed_at
            else:
                brief = {}
    capture = capture_path.read_text() if capture_path.exists() else ""

    return brief, capture, {
        "brief_file": str(brief_path) if brief else "",
        "brief_hash": _hash(json.dumps(brief, sort_keys=True, default=str)) if brief else "",
        "capture_file": str(capture_path) if capture_path.exists() else "",
        "capture_hash": _hash(capture) if capture else "",
        "capture_missing": not capture,
    }


def findings(html: str, brief: dict, capture: str) -> list[dict]:
    """Everything the checks can see, ordered so the sharp end is first."""
    where = []
    if brief.get("website_url"):
        where.append({"label": "The business's own site", "url": brief["website_url"]})
    for fact in brief.get("facts") or []:
        for source in (fact.get("sources") or [])[:1]:
            url = source.get("source_url")
            if url and not any(w["url"] == url for w in where):
                where.append({"label": f"{source.get('source_type','source')}"
                                       f" — {fact.get('label', fact.get('field'))}",
                              "url": url})

    found = list(checks.contradictions(html, brief, where))
    found += checks.mechanics(html, brief)
    found += checks.inventory(html, brief, capture, where)
    if not capture:
        found.insert(0, checks.Finding(
            stage="claim", verdict="unmeasured",
            title="No capture of the business's own site",
            detail="Every claim below is unsourced by default, because there is "
                   "nothing to check it against. Re-crawl before reading this as "
                   "evidence of anything."))
    return [f.as_row() for f in found]
