"""Phase 2 ("prove the seam"): the baseline reproduction.

Before building anything, reproduce the hand-checked result the round's
own instruction reports for a foreign (non-`render.py`) page built from
`hvac`'s own material. If this does not reproduce exactly, everything
built on top of it in this round is built on a wrong premise.

Confirms four things, each already true before this round touches
anything:

1. `render.unsupported()` is a phrase-in-a-bag-of-words match over
   *source* markup, not a sentence match over the *rendered* page — it
   catches "Since 1987" and "5 star" but misses "family-owned" and
   "licensed" (present as bare words elsewhere in hvac's own material)
   and misses the script-injected sentence entirely (it strips
   `<script>` from source rather than reading what the DOM becomes).
2. `provenance.unexplained_sentences()` reads five hard-coded CSS
   classes `render.py` itself emits. On markup that does not use them
   it sees zero sentences — not "clean", blind.
3. There is no gate wired at all for the review-count contradiction
   on a foreign page: `contradiction.reconcile()` is a pre-render
   transform on `Material`/free text, never invoked against arbitrary
   markup, and `pipeline._gate()` does not call it.
4. The credential invariant is `unsupported()` itself, over the
   credential-language patterns in `CLAIM_RE` — it inherits gap 1
   exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site.provenance import unexplained_sentences
from app.site.render import material_from_brief, unsupported

pytestmark = pytest.mark.unit

FOREIGN_HVAC_PAGE = """
<section class="hero"><h1>Cooling Dallas Since 1987</h1>
<p class="lead">Family-owned and fully licensed, we've served 40,000 homes.</p>
<p>Over 20,000 5 star reviews from happy neighbors.</p></section>
<script>document.body.insertAdjacentHTML('beforeend',
  '<p>Award-winning service, voted best in Texas.</p>')</script>
"""


def _hvac_material():
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    return material_from_brief(brief)


def test_unsupported_catches_some_of_the_page_but_not_all_of_it():
    """The bag-of-words gap (misses words present elsewhere in their own
    material) and the source-vs-rendered gap (misses the script-injected
    sentence) — both real, both already there before this round."""
    findings = unsupported(FOREIGN_HVAC_PAGE, _hvac_material())
    assert set(findings) == {"Since 1987", "5 star"}, findings
    # Named misses, not just "findings is incomplete" — these must NOT
    # be in the result, or the gap this round measures does not exist.
    assert not any("family-owned" in f.lower() for f in findings)
    assert not any("licensed" in f.lower() for f in findings)
    assert not any("award-winning" in f.lower() for f in findings)
    assert not any("voted" in f.lower() or "best" in f.lower() for f in findings)


def test_provenance_is_vacuous_on_markup_that_is_not_ours():
    """Zero sentences seen — not because the page has none, but because
    `_PROSE_RE` only reads classes `render.py` itself emits."""
    assert unexplained_sentences(FOREIGN_HVAC_PAGE, _hvac_material()) == []


def test_contradiction_reconcile_is_a_pre_render_transform_not_a_gate():
    """`contradiction.reconcile()` exists and works on free text, but
    nothing calls it against a rendered page — `pipeline._gate()`'s own
    call list is the proof, not an inference."""
    import inspect

    from app.site import contradiction, pipeline

    assert hasattr(contradiction, "reconcile")
    gate_source = inspect.getsource(pipeline._gate)
    assert "contradiction" not in gate_source, (
        "reconcile() is being called from _gate() now — the round's own "
        "premise (\"the contradiction check is not a gate\") no longer "
        "holds and Step 3 (\"contradiction: a real gate...\") needs to "
        "start from this file, not add one from nothing")


def test_credential_invariant_is_unsupported_over_claim_re_and_inherits_its_gaps():
    """Not a separate function — `unsupported()` run over the CLAIM_RE
    patterns that happen to be credential language. Same source-vs-
    rendered gap: the script-injected credential-shaped claim is missed
    exactly the same way "award-winning" was above."""
    page = """<p class="lead">We are fully insured.</p>
<script>document.body.insertAdjacentHTML('beforeend',
  '<p>State bar certified attorneys on staff.</p>')</script>"""
    findings = unsupported(page, _hvac_material())
    assert not any("certified" in f.lower() or "state bar" in f.lower()
                   for f in findings), findings
