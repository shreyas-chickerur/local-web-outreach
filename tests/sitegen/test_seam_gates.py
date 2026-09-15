"""Phase 2, Step 3: the ported gates, run against the planted-fabrication
corpus from Step 1. See `app/site/seam_gates.py` for what changed and why.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.claims import CLAIM_RE
from app.site import contractorfacts, provenance
from app.site.contradiction import contradicts
from app.site.render import material_from_brief, unsupported
from app.site.seam_gates import (
    _material_contractor_facts,
    contradicted_review_counts,
    gate,
    is_template_chrome,
    unbacked_numbers,
    unexplained_prose,
    unsupported_sentences,
)
from app.site.visible import VisibleRun, visible_text_runs

pytestmark = pytest.mark.unit

SEAM = Path("tests/fixtures/seam")
MANIFESTS = sorted(SEAM.glob("*-foreign.manifest.json"))
REAL_FIXTURES = Path("tests/fixtures/briefs")


def _load(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text())
    html = Path(manifest["source_page"]).read_text()
    brief = json.loads(Path(manifest["brief"]).read_text())
    material = material_from_brief(brief)
    return manifest, html, material


def _caught(planted_sentence: str, findings: list[str]) -> bool:
    lowered = planted_sentence.lower()
    return any(f.lower() in lowered or lowered in f.lower() for f in findings)


# ------------------------ the sentence-level bag-of-words fix -------------- #

def test_unsupported_sentences_closes_the_bag_of_words_gap():
    """The exact reproduction from test_seam_baseline.py, re-checked
    against the port: the old gate missed this because "certified"
    happens to appear somewhere in hvac's own material (a customer
    review). The port checks the SENTENCE, not the word."""
    manifest, html, material = _load(SEAM / "hvac-foreign.manifest.json")
    runs = visible_text_runs(html)
    findings = unsupported_sentences(runs, material)
    assert any("certified" in f.lower() for f in findings), findings


def test_unsupported_sentences_still_lets_a_verbatim_credential_claim_through():
    """The port must not become stricter than "verbatim or prefix-cut" —
    hvac's OWN material genuinely says "Licensed and Insured ... fully
    licensed" in its own block text. That sentence, said again verbatim,
    must not be flagged; only an uncorroborated ONE may be."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    page = '<body><p class="lead">Licensed and Insured</p></body>'
    runs = visible_text_runs(page)
    assert unsupported_sentences(runs, material) == []


def test_unsupported_sentences_backs_a_credential_via_contractorfacts_not_verbatim():
    """Step 2's own explicit path: "Licensed & insured" (contractorfacts.py's
    own phrasing, in a short <h3> badge -- not a literal match for hvac's
    real "Licensed and Insured ... fully licensed") must pass because
    contractorfacts.found() finds the SAME fact ("licensed_insured") in
    both the run and hvac's own material -- not because the run is short,
    and not because it happens to be a verbatim substring."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    page = '<h3>Licensed &amp; insured</h3>'
    runs = visible_text_runs(page)
    assert unsupported_sentences(runs, material) == []


def test_unsupported_sentences_runs_unconditionally_even_inside_a_button():
    """The credential invariant reopened (Phase 2b's gap 1): a claim
    inside <button>, with NOTHING in the material to corroborate it
    (threadbare has no about text, no blocks), must still be caught --
    this is the exact planted case, checked directly rather than only
    through the parametrized corpus sweep."""
    brief = json.loads(Path("tests/fixtures/briefs/threadbare.json").read_text())
    material = material_from_brief(brief)
    page = '<button>Board-certified, family-owned and voted #1 in Texas</button>'
    runs = visible_text_runs(page)
    findings = unsupported_sentences(runs, material)
    assert findings, "a claim inside <button> must not be exempt from CLAIM_RE"


# ------------------------------ unbacked_numbers ---------------------------- #

def test_unbacked_numbers_catches_an_invented_count_with_boilerplate_around_it():
    """Phase 2b's gap 2, closed: the exact reproduction case, with no
    five-star wording riding along for CLAIM_RE to coincidentally catch."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    page = "<p>4.9 average rating from 90,000 Google reviews</p>"
    runs = visible_text_runs(page)
    findings = unbacked_numbers(runs, material)
    assert "90,000" in findings, findings


def test_unbacked_numbers_accepts_the_real_corroborated_rating_and_review_count():
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    assert material.rating == 4.9
    assert material.reviews == 6203
    page = "<p>4.9 average rating from 6,203 Google reviews</p>"
    runs = visible_text_runs(page)
    assert unbacked_numbers(runs, material) == []


def test_unbacked_numbers_does_not_flag_24_7_as_a_quantity_claim():
    """"24/7" is an idiom for round-the-clock availability (the same
    reading contractorfacts.py's own "emergency" pattern already gives
    it), not two independent numbers to corroborate."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    page = "<p>Our technicians are available 24/7 for emergencies.</p>"
    runs = visible_text_runs(page)
    assert unbacked_numbers(runs, material) == []


def test_unbacked_numbers_skips_a_verbatim_matched_sentence_entirely():
    """A number inside a sentence that is itself verbatim/prefix-cut
    source material is backed by the sentence, not by the number
    matching a structured field -- the round's own second path."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    # Real, verbatim block text containing a number ("13 months") that
    # is not itself a corroborated structured field value.
    page = ("<p>Since November 2022, we&#8217;ve proudly served the Plano, "
           "TX community, providing reliable plumbing services for over "
           "13 months in the area.</p>")
    runs = visible_text_runs(page)
    assert unbacked_numbers(runs, material) == []


# --------------------------- the closed chrome rule ------------------------- #

def test_is_template_chrome_always_exempts_nav_label_and_form():
    assert is_template_chrome(VisibleRun(text="Contact", tag="nav", path="nav"))
    assert is_template_chrome(VisibleRun(text="Email address", tag="label", path="label"))
    assert is_template_chrome(VisibleRun(text="Newsletter signup form", tag="form", path="form"))


def test_is_template_chrome_exempts_a_short_button_or_link_only():
    """Phase 2b's own tightened rule: a or button is chrome only at
    three words or fewer. A longer one is prose -- threadbare's own
    planted button ("Board-certified, family-owned and voted #1 in
    Texas", 9 words) is exactly why "everything in <button>" (Phase 2's
    version) was too permissive."""
    assert is_template_chrome(VisibleRun(text="Book Now", tag="button", path="button"))
    assert is_template_chrome(VisibleRun(text="Learn more", tag="a", path="a"))
    assert not is_template_chrome(VisibleRun(
        text="Board-certified, family-owned and voted #1 in Texas",
        tag="button", path="button"))


def test_is_template_chrome_no_longer_exempts_headings_or_short_field_values():
    """Phase 2's version exempted any heading of <=3 words and any run
    of <=4 words with no terminal punctuation -- exactly the shape a
    planted short-form claim (class 7) takes, and exactly why the
    credential invariant reopened. Neither exemption survives Phase 2b:
    a heading or a bare stat now has to be backed like anything else
    (by unsupported_sentences/unbacked_numbers, not by being exempted
    from unexplained_prose here)."""
    assert not is_template_chrome(VisibleRun(text="Our Services", tag="h2", path="h2"))
    assert not is_template_chrome(VisibleRun(text="15,000+", tag="span", path="span"))
    assert not is_template_chrome(VisibleRun(text="$99", tag="div", path="div"))


def test_unexplained_prose_reads_prose_render_never_wrote_the_classes_for():
    """The whole point of the port: real content in a <div>, styled
    however a foreign page styles it, is checked — not silently passed
    because it is not one of five named CSS classes."""
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    page = ('<div class="whatever-a-foreign-page-calls-it">'
           'This sentence is invented and appears nowhere in the material.'
           '</div>')
    runs = visible_text_runs(page)
    findings = unexplained_prose(runs, material)
    assert findings == ["This sentence is invented and appears nowhere in the material."]


# ------------------------------ the contradiction gate ----------------------- #

def test_contradicted_review_counts_is_a_real_gate_now():
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    assert material.reviews == 6203
    page = '<p>Trusted by more than 15,000 reviews across North Texas.</p>'
    runs = visible_text_runs(page)
    findings = contradicted_review_counts(runs, material)
    assert findings, "a review-count contradiction with no five-star wording riding " \
                     "along must still be caught now that this is a real gate"
    assert contradicts(15000, 6203)


def test_contradicted_review_counts_lets_a_rounded_true_count_through():
    brief = json.loads(Path("tests/fixtures/briefs/hvac.json").read_text())
    material = material_from_brief(brief)
    page = '<p>Backed by over 6,000 verified reviews.</p>'
    runs = visible_text_runs(page)
    assert contradicted_review_counts(runs, material) == []


# ------------------------------ the planted corpus, ported ------------------ #

def _cases():
    for manifest_path in MANIFESTS:
        manifest, _, _ = _load(manifest_path)
        for planting in manifest["plantings"]:
            yield pytest.param(
                manifest_path, planting["class"], planting["sentence"],
                planting.get("script_injected", False),
                id=f"{manifest['business']}-class{planting['class']}")


@pytest.mark.parametrize("manifest_path,class_num,sentence,script_injected",
                        list(_cases()))
def test_the_ported_gate_catches_the_planted_fabrication(
        manifest_path, class_num, sentence, script_injected):
    """Reading SOURCE markup only (no browser — matching this test's own
    resource budget). Every class except 5 (script-injected) must be
    caught this way; class 5 is asserted separately below, since by
    construction it cannot be seen without actually running the script."""
    if script_injected:
        pytest.skip("class 5 requires a real render — see "
                    "test_class_5_is_caught_once_the_dom_is_actually_rendered")
    manifest, html, material = _load(manifest_path)
    runs = visible_text_runs(html)
    findings = gate(runs, material)
    assert _caught(sentence, findings), (
        f"class {class_num} ({manifest['business']}) not caught by the "
        f"ported gate: {sentence!r}. findings were: {findings}")


@pytest.mark.parametrize("manifest_path", MANIFESTS)
def test_class_5_is_caught_once_the_dom_is_actually_rendered(manifest_path):
    """No browser here either — a hand-simulated post-script DOM (the
    <script> tag's own insertAdjacentHTML call target, applied by hand)
    stands in for what app.site.visible.render() would actually produce.
    The real, literal browser render is proven separately in
    tests/sitegen/test_seam_corpus.py's real-Chrome test, which folds
    this exact fixture into the one browser session this round budgets
    for rather than opening a second one just to re-prove this."""
    manifest, html, material = _load(manifest_path)
    planting = next((p for p in manifest["plantings"] if p.get("script_injected")), None)
    if planting is None:
        pytest.skip(f"{manifest['business']} carries no script-injected "
                    f"planting (threadbare's page has no <script> at all, "
                    f"matching the round's own given snippet)")
    # Every seam fixture's script does exactly one insertAdjacentHTML
    # call into an empty slot div — simulate its effect directly rather
    # than parsing the <script> body.
    slot_id = "award-slot" if "award-slot" in html else "press-slot"
    injected = f'<p>{planting["sentence"]}</p>'
    post_script = html.replace(f'<div id="{slot_id}"></div>',
                              f'<div id="{slot_id}">{injected}</div>')
    assert post_script != html, "the fixture's slot div shape changed"
    runs = visible_text_runs(post_script)
    findings = gate(runs, material)
    assert _caught(planting["sentence"], findings), (
        f"class 5 ({manifest['business']}) not caught even once rendered: "
        f"{findings}")


@pytest.mark.parametrize("manifest_path", MANIFESTS)
def test_the_ported_gate_is_a_superset_of_the_old_gate_on_every_planted_page(manifest_path):
    """The "not weakened" claim, as a test rather than prose. For every
    planted page, read as SOURCE (the old gate never read rendered
    output, so this is the only fair comparison — class 5's
    script-injected addition is checked separately above and is not
    part of this claim): every claim phrase render.unsupported() finds
    must also appear somewhere in the ported gate's findings. The ported
    gate finding MORE (headings, numbers, credentials the old gate never
    checked) is expected and is not a superset violation; finding FEWER
    of the old gate's own claims would be."""
    manifest, html, material = _load(manifest_path)
    old_findings = unsupported(html, material)
    new_findings = gate(visible_text_runs(html), material)
    missing = [f for f in old_findings
              if not any(f.lower() in nf.lower() for nf in new_findings)]
    assert missing == [], (
        f"{manifest['business']}: the ported gate lost claims the old "
        f"gate caught: {missing} (old: {old_findings}, new: {new_findings})")


@pytest.mark.parametrize("business", ["hvac", "restaurant-casual"])
def test_the_control_page_is_still_not_flagged_by_the_ported_gate(business):
    """The port must not be MORE aggressive than the original on genuine
    verbatim content — a stricter sentence-level check could plausibly
    start flagging real prefix-cut source it shouldn't; this is what
    would catch that."""
    brief = json.loads(
        Path(f"tests/fixtures/briefs/{business}.json").read_text())
    material = material_from_brief(brief)
    html = (SEAM / f"{business}-control.html").read_text()
    runs = visible_text_runs(html)
    findings = gate(runs, material)
    assert findings == [], (
        f"{business} control page (verbatim-only, zero plantings) was "
        f"flagged by the ported gate: {findings}")


# --------------------- Phase 2c: widening the superset claim ---------------- #
#
# The superset test above only ever ran over the 3 hand-built manifests, and
# no planted sentence in them paired a corroborated credential with a second
# claim — which is exactly how class 8's gap (the whole-sentence
# `_credential_backed` exemption) got past it. Two more sweeps, per
# `.reviews/NEXT-ROUND.md`: every sentence of the real 19-fixture corpus's
# own rendered pages, and a generated set covering every corroborated
# credential of every real fixture paired with every CLAIM_RE shape, in one
# sentence — the exhaustive version of class 8, not just the one hand-picked
# example.

def _build_real_fixture_page(path: Path):
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec
    from app.store import db, leads, sites

    with db.session(":memory:") as conn:
        lead_id = leads.save_brief(conn, json.loads(path.read_text()))
        for stage in STAGES:
            run_stage(conn, lead_id, stage)
        brief = leads.brief_with_overrides(conn, lead_id)
        stored = sites.recall_stage(conn, lead_id, "direction") or {}
        config = dict(stored.get("config") or {})
        assert config.get("read_by") == "frozen", (
            f"{path.stem} did not replay a frozen direction")
        spec = spec_from_config(config)
        material = material_from_brief(brief)
        page = build_from_spec(brief, spec)
    return material, page


def test_the_ported_gate_is_a_superset_of_the_old_gate_on_every_real_fixture_page():
    """Same claim as the manifest version above, over every REAL fixture's
    own rendered page instead of hand-built foreign markup -- so the
    superset claim does not rest only on pages built for this test."""
    missing_by_fixture: dict[str, list[str]] = {}
    sentence_count = 0
    for path in sorted(REAL_FIXTURES.glob("*.json")):
        material, page = _build_real_fixture_page(path)
        runs = visible_text_runs(page)
        sentence_count += sum(
            len([s for s in provenance.SENTENCE_RE.split(r.text) if s.strip()])
            for r in runs)
        old_findings = unsupported(page, material)
        new_findings = gate(runs, material)
        missing = [f for f in old_findings
                  if not any(f.lower() in nf.lower() for nf in new_findings)]
        if missing:
            missing_by_fixture[path.stem] = missing
    assert missing_by_fixture == {}, (
        f"the ported gate lost claims the old gate caught on a real "
        f"fixture's own page: {missing_by_fixture}")
    assert sentence_count > 0


# One concrete, self-checked example per CLAIM_RE alternative (see
# app/core/claims.py) -- generated from the pattern by hand once, then
# proven still matching below, so a future edit to CLAIM_RE that adds or
# changes an alternative is caught here rather than silently narrowing what
# this sweep covers.
#
# "Ranked#1", not "#1" or "voted #1": found while writing this sweep, and
# reported rather than fixed (out of Part A's scope -- app/core/claims.py
# is not one of the files this round touches, and CLAIM_RE is shared with
# the vision pass, so widening it needs its own corpus-wide check).
# `\b#1\b` requires a WORD character immediately before "#" with no space,
# since "#" is itself non-word -- "#1", "the #1" and "voted #1" (the shape
# every real plant in this corpus actually uses) never match; only a form
# glued straight onto a preceding letter, like "Ranked#1", satisfies the
# \b on both sides. The "#1" alternative is effectively dead code against
# any natural sentence. See the handoff for this round.
_CLAIM_RE_EXAMPLES = (
    "since 1994", "est. 1994", "20+ years", "award-winning", "voted",
    "best in Texas", "number one", "Ranked#1", "family-owned", "family-run",
    "trusted by thousands", "500 happy customers", "five-star", "5-star",
    "licensed", "bonded", "insured", "certified", "accredited",
    "board-certified", "admitted to the bar", "state bar",
    "registered nurse",
)

# One phrase per contractorfacts.FACTS key that its OWN pattern matches --
# not always the section's printed LABEL (contractorfacts.py's own note:
# "Manufacturer certified" matches none of the manufacturer_badge patterns),
# so this is the trigger text a business's real material would need to say,
# checked below.
_FACT_TRIGGER_PHRASE: dict[str, str] = {
    "licensed_insured": "Licensed and insured",
    "emergency": "24/7 emergency service",
    "warranty": "backed by our workmanship warranty",
    "free_estimate": "ask about our free estimate",
    "service_area": "proudly serving the service area",
    "financing": "financing available",
    "manufacturer_badge": "an authorized dealer",
    "response_time": "same-day service",
    "admitted_to_bar": "admitted to the bar",
    "registered_practice": "a board-certified practice",
}


def test_claim_re_examples_actually_match_claim_re():
    for example in _CLAIM_RE_EXAMPLES:
        assert CLAIM_RE.search(example), example


def test_fact_trigger_phrases_actually_match_their_own_pattern():
    assert set(_FACT_TRIGGER_PHRASE) == {f.key for f in contractorfacts.FACTS}
    for fact in contractorfacts.FACTS:
        phrase = _FACT_TRIGGER_PHRASE[fact.key]
        assert fact.pattern.search(phrase), (fact.key, phrase)


def _credential_claim_cases():
    for path in sorted(REAL_FIXTURES.glob("*.json")):
        brief = json.loads(path.read_text())
        material = material_from_brief(brief)
        for key in sorted(_material_contractor_facts(material)):
            for claim in _CLAIM_RE_EXAMPLES:
                yield pytest.param(
                    path.stem, key, claim,
                    id=f"{path.stem}-{key}-{claim.replace(' ', '_')[:16]}")


_GENERATED_CASES = list(_credential_claim_cases())


def test_generated_cases_cover_every_real_fixtures_corroborated_credential():
    """A floor on the sweep itself: if this drops to 0, the corpus stopped
    corroborating any contractorfacts credential and the sweep below would
    pass vacuously."""
    assert len(_GENERATED_CASES) > 0


@pytest.mark.parametrize("slug,fact_key,claim", _GENERATED_CASES)
def test_a_generated_credential_plus_claim_sentence_is_still_caught(slug, fact_key, claim):
    """The exhaustive version of class 8: every corroborated credential of
    every real fixture, paired with every CLAIM_RE shape, in one sentence.
    A corroborated credential must never launder an invented claim riding
    beside it in the same sentence, whichever credential and whichever
    claim shape."""
    brief = json.loads((REAL_FIXTURES / f"{slug}.json").read_text())
    material = material_from_brief(brief)
    trigger = _FACT_TRIGGER_PHRASE[fact_key]
    sentence = f"{trigger}, and {claim}."
    page = f"<p>{sentence}</p>"
    runs = visible_text_runs(page)
    findings = gate(runs, material)
    assert any(claim.lower() in f.lower() or f.lower() in claim.lower()
              for f in findings), (
        f"{slug}: the corroborated credential {fact_key!r} laundered the "
        f"claim {claim!r} riding beside it in {sentence!r}: {findings}")
