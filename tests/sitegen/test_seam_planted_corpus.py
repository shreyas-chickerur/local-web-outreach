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
`_gate()` actually runs today. It documents which classes the currently
WIRED gate misses, not which classes the fixed one does (Step 3's
`test_seam_gates.py` is the one that must be all-green on every class).

Before the round after Phase 2c, this file was allowed to be red
overall — 12 (formerly 13; `class7d`'s "#1" planting started passing
here once CLAIM_RE's dead `#1` alternative was fixed) of its rows fail
by design, one baseline gap per (business, class). Left red, a real new
gap in the CURRENTLY WIRED gate (as opposed to the fixed one) could add
a 13th failure here and nobody would notice it wasn't one of the
already-known ones. `xfail(strict=True)` names each expected failure
individually instead: the file is green when nothing has changed, red
if a known gap gets fixed without updating this list (XPASS, under
`strict`, IS a failure) or a new gap opens up (a genuine, unmarked
failure). See `.reviews/phase-2c-seam.md` for the round that made this
change and confirmed each of these 12 against `9b7b6c5`/`c39e1cb`.
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

# (business, class) pairs the currently-wired gate (unsupported() +
# unexplained_sentences(), source markup, no browser) is known not to
# catch. classes 2/3/5/6 fail identically at 9b7b6c5 (Phase 2, before
# this corpus grew past its original six classes) -- genuinely
# pre-existing. 4b/7b (hvac) and 7a/7b (restaurant-casual) did not exist
# at 9b7b6c5 (Phase 2b's Step 1 added them) but were already failing,
# byte-identically, at c39e1cb (Phase 2b's own handoff, before Phase 2c
# touched anything) -- pre-existing relative to every round that could
# plausibly have fixed them without this file naming it a decision.
_KNOWN_GATE_GAPS: frozenset[tuple[str, str]] = frozenset({
    ("hvac", "2"), ("hvac", "3"), ("hvac", "5"), ("hvac", "6"),
    ("hvac", "4b"), ("hvac", "7b"),
    ("restaurant-casual", "2"), ("restaurant-casual", "3"),
    ("restaurant-casual", "5"), ("restaurant-casual", "6"),
    ("restaurant-casual", "7a"), ("restaurant-casual", "7b"),
})


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
            business = manifest["business"]
            class_num = str(planting["class"])
            marks = []
            if (business, class_num) in _KNOWN_GATE_GAPS:
                marks.append(pytest.mark.xfail(
                    strict=True,
                    reason=f"known gap in the currently-wired gate, class "
                           f"{class_num} ({business}) -- see "
                           f"_KNOWN_GATE_GAPS above and "
                           f".reviews/phase-2c-seam.md"))
            yield pytest.param(
                manifest_path, planting["class"], planting["sentence"],
                id=f"{business}-class{planting['class']}", marks=marks)


@pytest.mark.parametrize("manifest_path,class_num,sentence", list(_cases()))
def test_todays_gates_catch_the_planted_fabrication(manifest_path, class_num, sentence):
    """The baseline table, one row per planting. Every row not in
    `_KNOWN_GATE_GAPS` must pass; the ones IN it are `xfail(strict=True)`
    and must fail exactly as expected (see the module docstring) --
    either way this file is green on a normal run."""
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
