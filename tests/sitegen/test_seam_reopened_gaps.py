"""Phase 2b: the three gaps the Phase 2 port reopened, reproduced
independently before anything is changed.

Confirms, does not rediscover: all three reproduce exactly at `9b7b6c5`.
If any of them stopped reproducing, this file would need to say what
differs instead of silently building on a wrong premise.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site.render import material_from_brief, unsupported
from app.site.seam_gates import gate
from app.site.visible import visible_text_runs

pytestmark = pytest.mark.unit

_THREADBARE_CREDENTIAL_PAGE = """<header><h1>Licensed &amp; Insured</h1></header>
<div class=t><div>Since 1987</div></div>
<div class=t><div>25+ Years Experience</div></div>
<div class=t><div>Award-Winning Service</div></div>
<div class=t><div>BBB A+ Accredited</div></div>
<button>Board-certified, family-owned and voted #1 in Texas</button>
"""


def _threadbare_material():
    brief = json.loads(Path("tests/fixtures/briefs/threadbare.json").read_text())
    return material_from_brief(brief)


def test_gap_1_the_credential_invariant_is_reopened():
    """`is_template_chrome()` exempts short runs and everything in
    <button> from `unsupported_sentences()` entirely -- so a page with
    NO corroborating material for any of it still comes back clean.
    threadbare has no about text and no blocks (confirmed below,
    not assumed), so every one of these 9 claims is genuinely
    uncorroborated."""
    material = _threadbare_material()
    assert material.about is None
    assert material.blocks == ()

    old_findings = unsupported(_THREADBARE_CREDENTIAL_PAGE, material)
    assert len(old_findings) == 9, old_findings

    runs = visible_text_runs(_THREADBARE_CREDENTIAL_PAGE)
    new_findings = gate(runs, material)
    assert new_findings == [], (
        f"expected the reopened gap (0 findings) at 9b7b6c5; got {new_findings}. "
        f"If this is no longer empty, the premise for Step 2 has changed.")


def test_gap_2_an_invented_number_is_never_checked():
    """`_is_all_facts_and_boilerplate()` only scans `[a-z]+` runs, so a
    digit is invisible to it -- an invented review count is chrome as
    long as the words around it are boilerplate. The contradiction gate
    separately misses it because REVIEW_COUNT_RE requires the number
    immediately beside "review(s)", and "Google" sits between them
    here."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    assert material.reviews == 6203

    html = "<p>4.9 average rating from 90,000 Google reviews</p>"
    runs = visible_text_runs(html)
    findings = gate(runs, material)
    assert findings == [], (
        f"expected the reopened gap (0 findings) at 9b7b6c5; got {findings}. "
        f"If this is no longer empty, the premise for Step 2 has changed.")


def test_gap_3_nothing_references_the_real_design_page():
    """The 40-finding classification from Phase 2's handoff exists only
    as prose in .reviews/phase-2-seam.md -- no test or tool re-derives
    it. This test itself is the reproduction: it exists to fail loudly
    (an AssertionError naming the missing file) until Step 4 adds the
    real one, rather than let the gap go unnoticed a second time."""
    referencing = [
        p for p in Path("tests").rglob("*.py")
        if p.name != "test_seam_reopened_gaps.py"
        and "hvac-claude-design" in p.read_text()
    ]
    assert referencing == [], (
        "a test now references the design page export -- update this "
        "test's own premise rather than leaving it claiming a gap that "
        "is already closed")
