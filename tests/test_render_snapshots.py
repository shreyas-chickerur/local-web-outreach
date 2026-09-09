"""A snapshot of every fixture's rendered HTML — "rest of F": snapshot tests
over the fixtures.

The fingerprint already catches a moved AXIS (`test_the_instrument_
reproduces.py`) and the committed contact sheet already catches a STALE
picture (`test_the_committed_sheet_shows_the_corpus_that_shipped`). Neither
catches a change that moves neither: a rewritten sentence, a renamed CSS
class, a section's markup restructured with the same axis value and the
same words. This is the net under both — a hash of the exact bytes
`build_from_spec` produces, one per fixture, so ANY unintended change to
the actual rendered output fails here rather than being noticed later by a
person scrolling a contact sheet.

A failure here is not necessarily wrong — it means the rendered output
changed, and the change should be reviewed and the snapshot updated
deliberately (regenerate `tests/fixtures/render_snapshots.json`, the same
way a fingerprint ruler gets re-pinned), not a signal to weaken the test.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")
SNAPSHOTS = Path("tests/fixtures/render_snapshots.json")


def test_every_fixture_still_renders_the_pinned_bytes():
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec
    from app.store import db, leads, sites

    pinned = json.loads(SNAPSHOTS.read_text())
    current: dict[str, str] = {}
    with db.session(":memory:") as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            slug = path.stem
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            config = dict(stored.get("config") or {})
            assert config.get("read_by") == "frozen", (
                f"{slug} did not replay a frozen direction — these hashes "
                f"would be taken against a different system than the one "
                f"that pinned them")
            spec = spec_from_config(config)
            page = build_from_spec(brief, spec)
            current[slug] = hashlib.sha256(page.encode()).hexdigest()

    assert set(current) == set(pinned), (
        f"the corpus and the snapshot file disagree on which fixtures "
        f"exist: {set(current) ^ set(pinned)}")
    moved = sorted(slug for slug in current if current[slug] != pinned[slug])
    assert not moved, (
        f"the rendered output moved for {moved} with no corresponding "
        f"axis or content change caught elsewhere. If this is deliberate, "
        f"regenerate {SNAPSHOTS} and say why in the commit — do not edit "
        f"the hashes by hand.")
