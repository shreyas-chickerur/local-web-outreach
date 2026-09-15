"""Phase 2b, Step 4: the real Claude Design page, reproducible.

Closes gap 3 (nothing referenced `tests/fixtures/seam/
hvac-claude-design.html` — Phase 2's 40-finding classification existed
only as prose). Pure Python, no browser: the design content is the
`content.files["Main.dc.html"]` entry inside the committed export's own
`<script id="appifact-doc">` state block — a plain JSON document, not
something that needs a runtime `srcdoc` assignment to read. See
`.reviews/phase-2-design-page-findings.md` for the full,
sentence-by-sentence classification this pins the count of.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.site.render import material_from_brief
from app.site.seam_gates import gate
from app.site.visible import visible_text_runs

pytestmark = pytest.mark.unit

DESIGN_PAGE = Path("tests/fixtures/seam/hvac-claude-design.html")

_STATE_BLOCK_RE = re.compile(
    r'<script[^>]*id=["\']appifact-doc["\'][^>]*>(.*?)</script>', re.S)


def extract_main_dc_html(export_html: str) -> str:
    """The design content, not the editor. A design canvas export is a
    bundled page (2.5MB; ~483K characters sit outside <script> tags, and
    even that is the EDITOR's own chrome — toolbar labels — not the
    design: the actual homepage renders into a sandboxed, opaque-origin
    preview iframe set via a runtime `srcdoc` assignment at view time,
    invisible to the outer document's own DOM). The design source itself
    is simpler than that: `content.files["Main.dc.html"]` in the state
    block's own JSON, no rendering required to reach it.
    """
    match = _STATE_BLOCK_RE.search(export_html)
    assert match, "no appifact-doc state block found in the export"
    data = json.loads(match.group(1))
    return data["content"]["files"]["Main.dc.html"]


def test_the_export_is_a_bundled_canvas():
    """Confirms, does not rediscover: the same shape the round's own
    restaurant-rich example carries, and the reason gap 3 needed a real
    extraction path rather than a source-markup read."""
    export_html = DESIGN_PAGE.read_text()
    stripped = re.sub(r"<script[^>]*>.*?</script>", " ", export_html, flags=re.S)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    assert len(export_html) > 1_000_000
    assert len(stripped) < len(export_html) * 0.25


def test_extraction_finds_real_design_content_not_the_editor_chrome():
    main = extract_main_dc_html(DESIGN_PAGE.read_text())
    assert "trusted plumbers" in main.lower()
    assert "Jeff Willie" in main
    # The one unresolved piece -- a CSS color hole, never visible text.
    assert "{{accent}}" in main


def test_the_gate_finding_count_is_pinned():
    """The reproducible version of Phase 2's 40-finding claim. The count
    moved to 42 in Phase 2b (unbacked_numbers() and the tightened
    provenance rule are both new since Phase 2's own 40), then to 48 in
    Phase 2c: `_credential_backed_remainder` (`.reviews/NEXT-ROUND.md`)
    exempts only a credential's own matched span, not the whole sentence
    -- 6 sentences on this real page were previously hidden entirely by
    the whole-sentence version, each one a real "Licensed & insured" /
    "24/7 emergency" / "Same-day service" credential riding beside its
    own true-reworded caption that the OLD, narrower provenance check
    would have flagged on its own had the credential exemption not
    swallowed the whole sentence first. Pinned here so a future change to
    either gate or this page is a deliberate, visible decision, not a
    silent drift. Every finding is classified in
    .reviews/phase-2-design-page-findings.md.
    """
    main = extract_main_dc_html(DESIGN_PAGE.read_text())
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    runs = visible_text_runs(main)
    findings = gate(runs, material)
    assert len(findings) == 48, (
        f"expected 48 findings, got {len(findings)}: {findings}")
