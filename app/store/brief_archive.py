"""Every crawled brief, kept — never overwritten.

`leads.save_brief` overwrites the DB's cached copy on every re-crawl,
which is correct for a fast "what do we currently believe" read, but it
means the fact of an EARLIER crawl disappears the moment a new one
lands. This archive is the permanent trail alongside it:
`sites/<lead-slug>/briefs/<ISO-timestamp>.json`, one new file per crawl, never
overwritten, plus its own content hash — so a later review can always
answer "what did the model actually see" by naming the exact file and
hash the design prompt was built from, not a row that has since been
overwritten twice.

Operator corrections are NOT re-archived here — those already stack
through `leads.brief_with_overrides`'s event trail, a separate,
already-permanent mechanism (`app/store/leads.py`). This archive is for
the raw crawl only: what the site said, not what you were told at the
door.

Only called from the two real research entry points (`app.cli.cmd_brief`,
`app.web.server.lookup`) — never from `build_brief()` itself, so a unit
test that calls `build_brief()` directly (every one of them, today, uses
a fake fetcher) never writes to disk as a side effect of being a test.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.store import folders

# Unset, crawls go in each business's own folder (`app.store.folders`). A
# test or a caller that sets this gets `<root>/<slug>/briefs/` instead.
ARCHIVE_ROOT: Path | None = None
_slug = folders.slug


def directory(name: str, root: Path | None = None) -> Path:
    """Where one business's crawls are kept."""
    return folders.of(name, root if root is not None else ARCHIVE_ROOT) / "briefs"


def _content_hash(brief_json: dict) -> str:
    canonical = json.dumps(brief_json, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def save(brief_json: dict, *, root: Path | None = None) -> dict:
    """Write a new, timestamped, never-overwritten copy of this brief.

    Returns `{"path", "hash", "captured_at"}` — the exact reference
    `app.site.opening.full_digest` cites in the design prompt, so a
    revision can always be traced back to the real file it was built
    from.
    """
    # NOT a `root: Path = ARCHIVE_ROOT` default: a default argument value
    # is bound once, when this function is DEFINED, so a test that
    # monkeypatches the module-level `ARCHIVE_ROOT` afterward would
    # silently have no effect on a caller that omits `root` — exactly the
    # kind of bug this project's own `_stage_direction`/gate story (BRIEF
    # §1) already warns about with mutable module state. Read fresh here
    # instead, so monkeypatching `ARCHIVE_ROOT` actually works.
    name = brief_json.get("name") or "unnamed"
    folder = directory(str(name), root)
    folder.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    captured_at = now.isoformat(timespec="seconds")
    content_hash = _content_hash(brief_json)
    # Microsecond precision in the FILENAME only (the reported `captured_at`
    # stays second-precision, which is all a human reading it needs) — two
    # crawls landing in the same second is not a hypothetical (a retried
    # request, two fast test runs) and "never overwrite" has to hold then
    # too, not just for crawls a human would notice were separate. Colons
    # in an ISO timestamp are also not a safe filename character on every
    # filesystem this project might run on.
    stamp = now.isoformat(timespec="microseconds").replace(":", "-")
    path = folder / f"{stamp}.json"
    path.write_text(json.dumps(brief_json, indent=2, sort_keys=False) + "\n")

    pointer = {"path": str(path), "hash": content_hash, "captured_at": captured_at}
    (folder / "current.json").write_text(json.dumps(pointer, indent=2) + "\n")
    return pointer


def current(name: str, *, root: Path | None = None) -> dict | None:
    """The most recently archived brief's own pointer, or `None` if this
    business has never been crawled before."""
    path = directory(name, root) / "current.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
