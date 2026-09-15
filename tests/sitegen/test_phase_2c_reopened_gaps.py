"""Phase 2c: two claims in the Phase 2b handoff (`.reviews/phase-2b-seam.md`)
that do not hold, found by independent review (`.reviews/NEXT-ROUND.md`) and
reproduced here exactly as given, before anything was changed.

Gap 1 — the ported gate is not a superset of the old one. `_credential_backed()`
exempts the WHOLE sentence a corroborated credential sits in, not just its own
matched span — so one true credential vouches for every other claim it shares
a sentence with. The bag-of-words laundering gap Phase 2b closed once, one
level up.

Gap 2 — Phase 2b's widened `REVIEW_COUNT_RE` reads an "N+" claim as an exact
`N`, so a true lower-bound statement ("100+ Google reviews", corroborated
count 136) now reads as contradicting the very count it is consistent with,
and `reconcile()` drops it from a real, shipped page (`roofer-rich`) that no
Phase 2b commit was supposed to touch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site.contradiction import contradicts
from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.render import build_from_spec, material_from_brief, unsupported
from app.site.seam_gates import gate
from app.site.visible import visible_text_runs
from app.store import db, leads, sites

pytestmark = pytest.mark.unit


def test_gap_1_a_corroborated_credential_no_longer_launders_the_whole_sentence():
    """hvac's own material corroborates `licensed_insured` (their own block
    text says "Licensed and Insured ... fully licensed"). A sentence pairing
    that real credential with two invented superlatives must still be caught
    for the invented half -- `render.unsupported()` (old) catches
    'award-winning' and 'best in'; the ported gate must too."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    page = "<p>Licensed and insured, award-winning and voted best in Plano.</p>"

    old_findings = unsupported(page, material)
    assert old_findings, "the reproduction itself changed -- old gate finds nothing"

    runs = visible_text_runs(page)
    new_findings = gate(runs, material)
    missing = [f for f in old_findings
              if not any(f.lower() in nf.lower() for nf in new_findings)]
    assert missing == [], (
        f"a corroborated credential laundered the rest of its own sentence: "
        f"old={old_findings} new={new_findings}")


def test_gap_2_a_true_lower_bound_review_count_is_not_a_contradiction():
    """roofer-rich's own material says '100+ Google reviews' and '100+
    verified reviews'; the corroborated count is 136, which satisfies both
    floors. Neither sentence contradicts the corroborated count."""
    assert not contradicts(100, 136), (
        "'100+' now reads as an exact 100, not a floor 136 satisfies")


def test_gap_2_the_shipped_roofer_rich_page_still_carries_its_real_review_count():
    """The actual end-to-end reproduction: build roofer-rich exactly as the
    pipeline does and confirm the corroborated count survives render. At
    c39e1cb this fails -- 100+ is silently dropped from the page, per
    .reviews/phase-2b-seam.md's own (incorrect) "pre-existing" attribution."""
    path = Path("tests/fixtures/briefs/roofer-rich.json")
    with db.session(":memory:") as conn:
        lead_id = leads.save_brief(conn, json.loads(path.read_text()))
        for stage in STAGES:
            run_stage(conn, lead_id, stage)
        brief = leads.brief_with_overrides(conn, lead_id)
        stored = sites.recall_stage(conn, lead_id, "direction") or {}
        config = dict(stored.get("config") or {})
        assert config.get("read_by") == "frozen"
        spec = spec_from_config(config)
        page = build_from_spec(brief, spec)

    assert "136" in page, "the corroborated review count should still print"
    assert "100+" in page, (
        "a true lower-bound claim their own material states was dropped as "
        "if it contradicted the corroborated count it is actually consistent "
        "with")
