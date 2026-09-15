"""Phase 2, Step 1: the planted-fabrication corpus, and its baseline.

`tests/fixtures/seam/` carries two hand-built foreign pages (`hvac`,
`restaurant-casual`) with one planted fabrication per class (1-6, see
each page's own `.manifest.json`), plus a matching control page per
business made only of verbatim/prefix-cut spans of real material —
so a gate that flags everything is caught too, not just a gate that
misses everything.

This file is the BASELINE, run against today's gates exactly as
`pipeline._gate()` combines them (`unsupported()` + `unexplained_
sentences()`), reading SOURCE markup only — no browser, matching how
`_gate()` actually runs today. It is expected to be red: that is the
point of this step. Step 3 ports the gates onto a rendered-DOM read
and reports the same table again, after.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site.provenance import unexplained_sentences
from app.site.render import material_from_brief, unsupported

pytestmark = pytest.mark.unit

SEAM = Path("tests/fixtures/seam")
MANIFESTS = sorted(SEAM.glob("*-foreign.manifest.json"))


def _load(manifest_path: Path) -> tuple[dict, str, object]:
    manifest = json.loads(manifest_path.read_text())
    html = Path(manifest["source_page"]).read_text()
    brief = json.loads(Path(manifest["brief"]).read_text())
    material = material_from_brief(brief)
    return manifest, html, material


def _current_gate_findings(html: str, material) -> list[str]:
    """Exactly what `pipeline._gate()` runs today — the two functions,
    concatenated, nothing more."""
    return unsupported(html, material) + unexplained_sentences(html, material)


def _caught(planted_sentence: str, findings: list[str]) -> bool:
    """Does any finding account for this planted sentence?

    `unsupported()` returns a short CLAIM fragment (e.g. "5 star"), not
    the whole sentence; `unexplained_sentences()` returns the whole
    sentence. Either shape counts as "caught" — a fragment match still
    means the gate flagged something on the page tied to this planting."""
    lowered = planted_sentence.lower()
    return any(f.lower() in lowered or lowered in f.lower() for f in findings)


def _cases():
    for manifest_path in MANIFESTS:
        manifest, _, _ = _load(manifest_path)
        for planting in manifest["plantings"]:
            yield pytest.param(
                manifest_path, planting["class"], planting["sentence"],
                id=f"{manifest['business']}-class{planting['class']}")


@pytest.mark.parametrize("manifest_path,class_num,sentence", list(_cases()))
def test_todays_gates_catch_the_planted_fabrication(manifest_path, class_num, sentence):
    """The baseline table, one row per planting. Expected RED overall —
    see the module docstring. A row that already passes says today's
    gate happens to catch that shape; it is not evidence the gate reads
    the rendered page (see the control-page test below for that)."""
    manifest, html, material = _load(manifest_path)
    findings = _current_gate_findings(html, material)
    assert _caught(sentence, findings), (
        f"class {class_num} ({manifest['business']}) not caught by "
        f"today's gates: {sentence!r}. findings were: {findings}")


@pytest.mark.parametrize("business", ["hvac", "restaurant-casual"])
def test_the_control_page_is_not_flagged_by_todays_gates(business):
    """Zero plantings, verbatim/prefix-cut spans only. A gate that flags
    everything regardless of content would pass every row above for the
    wrong reason; this is what catches that.

    NOTE, read alongside the module docstring: this passing today is not
    proof the gate is discriminating correctly on foreign markup — it is
    also exactly what `unexplained_sentences()` returns on ANY foreign
    page, discriminating or not (`_PROSE_RE` matches none of this markup's
    classes, so it returns [] here for the same reason it returned [] on
    the hvac reproduction in test_seam_baseline.py). Only `unsupported()`
    is doing real work on this page, and only because CLAIM_RE happens
    not to match any of the verbatim spans chosen."""
    brief = json.loads(
        Path(f"tests/fixtures/briefs/{business}.json").read_text())
    material = material_from_brief(brief)
    html = (SEAM / f"{business}-control.html").read_text()
    findings = _current_gate_findings(html, material)
    assert findings == [], (
        f"{business} control page (verbatim-only, zero plantings) was "
        f"flagged: {findings}")
