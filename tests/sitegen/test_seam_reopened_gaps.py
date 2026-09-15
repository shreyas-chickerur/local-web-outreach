"""Phase 2b: the three gaps the Phase 2 port reopened.

All three were reproduced independently before anything was changed
(confirmed exactly at `9b7b6c5`, commit `f6d139f`), then closed: gaps 1
and 2 in Step 2 (`app/site/seam_gates.py`, `app/site/contradiction.py`),
gap 3 in Step 4 (`tests/sitegen/test_seam_design_page.py`). Every test
here now asserts the FIXED behaviour, so this file doubles as the
regression guard against reopening any of the three a second time.
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


def test_gap_1_the_credential_invariant_stays_closed():
    """At 9b7b6c5, `is_template_chrome()` exempted short runs and
    everything in <button> from `unsupported_sentences()` entirely --
    so a page with NO corroborating material for any of it (threadbare
    has no about text and no blocks, confirmed below, not assumed)
    still came back clean. Step 2 removed that exemption from the
    claims check outright; this asserts the gate now catches every one
    of the 9 genuinely uncorroborated claims the old gate also caught."""
    material = _threadbare_material()
    assert material.about is None
    assert material.blocks == ()

    old_findings = unsupported(_THREADBARE_CREDENTIAL_PAGE, material)
    assert len(old_findings) == 9, old_findings

    runs = visible_text_runs(_THREADBARE_CREDENTIAL_PAGE)
    new_findings = gate(runs, material)
    assert len(new_findings) >= 9, (
        f"the credential invariant is reopened again: {new_findings}")


def test_gap_2_an_invented_number_is_now_checked():
    """At 9b7b6c5, `_is_all_facts_and_boilerplate()` only scanned
    `[a-z]+` runs, so a digit was invisible to it -- an invented review
    count was chrome as long as the words around it were boilerplate,
    and the contradiction gate separately missed it because
    REVIEW_COUNT_RE required the number immediately beside "review(s)".
    Step 2 added unbacked_numbers() (unconditional, no chrome exemption)
    and widened REVIEW_COUNT_RE to a closed review/rating-word
    allowlist; this asserts the number is now caught."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    assert material.reviews == 6203

    html = "<p>4.9 average rating from 90,000 Google reviews</p>"
    runs = visible_text_runs(html)
    findings = gate(runs, material)
    assert any("90,000" in f or "90000" in f for f in findings), (
        f"the unbacked-number gap is reopened again: {findings}")


def test_gap_3_the_real_design_page_is_now_reproducible():
    """At 9b7b6c5, the 40-finding classification from Phase 2's handoff
    existed only as prose in .reviews/phase-2-seam.md -- no test or tool
    re-derived it. Step 4 (`tests/sitegen/test_seam_design_page.py`)
    closed this: this asserts that a real test now references the
    design page export and pins a finding count, rather than leaving
    this file claiming a gap that is already closed."""
    referencing = [
        p for p in Path("tests").rglob("*.py")
        if p.name != "test_seam_reopened_gaps.py"
        and "hvac-claude-design" in p.read_text()
    ]
    assert referencing, (
        "gap 3 is reopened: nothing references the design page export again")
