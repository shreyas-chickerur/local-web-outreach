"""Phase 3: playbooks are prose a page is scored against, not code — but
"which exact revision was this page scored against" has to be answerable
without diffing markdown files by eye. `content_hash()` is the whole
contract: read the file, hash it, record the hash beside anything that
claims to have been scored against it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PLAYBOOKS_DIR = Path(__file__).parent / "playbooks"


def content_hash(name: str) -> str:
    """First 12 hex chars of the sha256 of `playbooks/{name}.md` — long
    enough to be practically unique across the handful of playbooks this
    project will ever have, short enough to read in a handoff table."""
    text = load(name)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def load(name: str) -> str:
    return (PLAYBOOKS_DIR / f"{name}.md").read_text()
