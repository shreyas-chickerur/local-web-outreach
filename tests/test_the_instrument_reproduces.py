"""The census must produce the pinned numbers from a clean checkout.

This is the claim the whole instrument rests on: that the fixtures are
self-sufficient, that a clean clone measures the same system, and that the
pinned baseline means something to somebody who was not here when it was taken.

It was verified by hand once — cache moved aside, no network, no key — and a
hand verification does not persist and nobody can repeat it. That is the same
shape as everything else this project keeps catching: something that looks like
it is in force because a person remembers doing it.

Runs with no key, no cache and no network, because that is the state a reviewer
arrives in.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site import agreement
from app.site import fingerprint as fp

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")

# The pinned reading, and the rulers it was taken with. These move only in a
# commit that says they moved and why — a number that changes because the
# instrument changed is not a result.
RULER = "4616d461"
RULE = "a83a0283"
LABELS = "69061e09"
# The held-out third, frozen verbatim. It moves only when a pair is
# RETIRED, never when one is re-judged.
HELD_OUT = "f4ed374b"
SAME_TRADE_MEAN = 0.51
# 21 of 36, on nine axes, against thirteen verdicts re-judged blind after type
# treatment landed and the corpus was re-decided under it.
#
# It is not comparable to the 14 of 22 before it: different axes, different
# corpus, different labels. What is comparable is the pre-registered claim, and
# that claim FAILED — see `test_the_blind_spot_did_not_clear`.
AGREEMENT = (39, 55)


def fingerprints() -> dict[str, fp.Fingerprint]:
    """Every fixture's vector, taken the way the census takes it.

    Through the database and `brief_with_overrides`, not off the raw JSON — two
    paths to the same number drift, and that is the defect this project keeps
    finding. A reviewer runs the census; so does this.
    """
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import material_from_brief, plan_for
    from app.store import db, leads, sites

    out: dict[str, fp.Fingerprint] = {}
    with db.session(":memory:") as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            lead = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead, stage)
            brief = leads.brief_with_overrides(conn, lead)
            stored = sites.recall_stage(conn, lead, "direction") or {}
            config = dict(stored.get("config") or {})
            assert config.get("read_by") == "frozen", (
                f"{path.stem} did not replay a frozen direction — these "
                f"numbers would be measured against a different system than "
                f"the one that pinned them")
            spec = spec_from_config(config)
            out[path.stem] = fp.of(plan_for(brief, spec), spec,
                                   material_from_brief(brief))
    return out


def test_both_rulers_recompute_to_the_pinned_values():
    """If either moved, every number below is incomparable to its baseline and
    the census says so rather than reporting a difference."""
    assert fp.metric_version() == RULER
    assert fp.rule_version() == RULE, (
        "the gate's rule moved. Every fixture's frozen direction is an answer "
        "that rule accepted, so re-decide the corpus (tools/make_fixtures.py "
        "--redecide) and re-pin, rather than reporting the old baseline "
        "against a corpus the gate rebuilt underneath it")
    assert agreement.labels_version() == LABELS


def test_the_pinned_baseline_matches_what_the_census_asserts():
    """Two copies of the same number drift. The tool's constants are the ones
    the census prints, so this fails if they part company."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "census", Path("tools/quality_census.py"))
    census = importlib.util.module_from_spec(spec)
    sys.modules["census"] = census
    spec.loader.exec_module(census)
    assert census.BASELINE_METRIC == RULER
    assert census.BASELINE_RULE == RULE
    assert census.BASELINE_LABELS == LABELS
    assert census.BASELINE_SAME_TRADE == pytest.approx(SAME_TRADE_MEAN, abs=0.01)


def test_the_fixtures_are_self_sufficient_with_no_key_and_no_cache():
    """No model call, no network, no `artifacts/fixtures.db` — the state a
    reviewer arrives in. Every fixture still scores a hero from what it
    carries, and the subjects vary."""
    prints = fingerprints()
    assert len(prints) >= 11
    subjects = {f.values["hero_subject"] for f in prints.values()}
    assert len(subjects) >= 4, subjects
    # `threadbare` has one photograph and vision condemned it, so the floor
    # refuses it and the page leads with no hero at all.
    assert prints["threadbare"].values["hero_subject"] == "-"


def test_the_same_trade_mean_is_the_pinned_number():
    """The headline of the census, recomputed here so a clean checkout proves
    it rather than being told."""
    from app.site.render import trade_kind

    prints = fingerprints()
    trades = {}
    for slug, _ in prints.items():
        brief = json.loads((FIXTURES / f"{slug}.json").read_text())
        trades[slug] = trade_kind(brief.get("trade"))

    # Excluding what cannot be judged, the same way the census does — one
    # definition of the scored corpus, imported rather than restated. An empty
    # page sits further from its trade-mates than any real pair, so counting it
    # reads as variety and is an absence.
    slugs = [s for s in sorted(prints) if s not in agreement.UNSCORED]
    same_trade = [fp.distance(prints[a], prints[b])
                  for i, a in enumerate(slugs) for b in slugs[i + 1:]
                  if trades[a] == trades[b]]
    assert len(same_trade) == 7, (
        f"{len(same_trade)} scored same-trade pairs, expected 7 — the corpus "
        f"or the exclusion list moved, and the pinned mean is about a "
        f"different set of pairs than the one being measured")
    assert same_trade, "no two fixtures share a trade — the corpus cannot test this"
    mean = sum(same_trade) / len(same_trade)
    assert mean == pytest.approx(SAME_TRADE_MEAN, abs=0.02), (
        f"same-trade mean is {mean:.0%}, pinned at {SAME_TRADE_MEAN:.0%}. "
        f"If this moved on purpose, re-pin it in tools/quality_census.py and "
        f"here, in the same commit, and say why.")


def test_agreement_against_the_blind_labels_is_the_pinned_score():
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    score = agreement.score(distances)
    assert (score.ordered, score.comparisons) == AGREEMENT, score.report()
    assert score.labels == LABELS


def test_the_inversions_are_the_ones_that_were_looked_at():
    """The pre-registered claim in `.reviews/slice-b-predictions.md` binds on
    first-screen contract AND type treatment, and only one of those has landed,
    so it is still open. What is worth recording is that `dentist`/`law`
    resolved on the first axis alone and then came back: re-deciding the corpus
    under the corrected gate rule put both of them on `proof`, and judged blind
    they are one page in two colours again. An interim resolution is not the
    claim being paid off.

    So this pins the inversions rather than asserting there are none. Every one
    of them is a pair a person called the same site and the vector ranked
    further apart than a pair they called different — which is the case for the
    next axis, not something to assert away. If the set changes, say why in the
    commit that changes it.
    """
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    inversions = agreement.score(distances).inversions
    same_pairs = sorted({pair for pair, _, _, _ in inversions})
    assert same_pairs == ["barbecue/restaurant-bare", "dentist/hvac",
                          "restaurant-bare/restaurant-rich",
                          "roofer/salon"], (
        f"the inversions moved: {same_pairs}. Re-judge blind before accepting "
        f"it, per .reviews/slice-b-predictions.md")


def test_the_held_out_verdicts_are_not_re_judged():
    """The set exists to be unavailable to whoever is tuning.

    Changing the gate's rule re-decides the corpus, which re-renders the pages,
    which makes the verdicts describing them stale, which invites a re-judge —
    and a rule tuned against labels taken from the corpus that rule produced is
    fitting with extra steps. That loop can only ever produce "it settled and
    satisfies its own gate", whether the rule is right or not.

    So one verdict in three, chosen by a hash of the slugs rather than by
    anybody, is scored and never tuned against. When its rendering goes stale
    it is retired with a reason, which shrinks the set — that is the cost, and
    it is cheaper than a number that cannot mean anything.

    This is hashed over the reasoning as well as the verdict, because the quiet
    way back in is not to flip a verdict but to reword it.
    """
    assert agreement.held_out_version() == HELD_OUT, (
        "a held-out verdict changed. If a page moved under one, RETIRE it — "
        "add `retired` saying why, and re-pin HELD_OUT in the same commit. Do "
        "not re-judge it.")


def test_the_held_out_third_is_scored_separately():
    """Reported apart from the tuning set, so the two numbers cannot be
    confused. It starts at this commit, so it says nothing about the rule
    landing here — the first rule it can honestly score is the next one."""
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    held = agreement.score(distances, agreement.load(held_out=True))
    tuned = agreement.score(distances, agreement.load(held_out=False))
    assert held.comparisons and tuned.comparisons, (
        "one side of the split has no scorable comparisons — the set is too "
        "small to hold anything out, and saying so is better than reporting a "
        "number taken from nothing")
    assert (held.ordered, held.comparisons) == (0, 3)
    assert (tuned.ordered, tuned.comparisons) == (27, 32)


SHEET = Path(".reviews/sheet/index.html")


def test_the_committed_sheet_shows_the_corpus_that_shipped():
    """The pictures a verdict is read off must be the pages that shipped.

    The sheet was captured nine minutes before the fixtures it was committed
    beside were re-frozen, so the committed copy showed five pre-gate pages
    while its own captions claimed otherwise — and a blind re-judge taken off
    it would have been a judgement of pages that no longer existed. Nothing
    caught it: `_judged_against` says "re-look at the sheet" in prose, and
    `labels_version` hashes the verdicts rather than the rendering.

    The vector is printed under every thumbnail, so this is checkable. If it
    fails, regenerate the sheet — do not edit the captions.
    """
    import re

    assert SHEET.exists(), "no committed contact sheet to check"
    html = SHEET.read_text()
    printed: dict[str, dict[str, str]] = {}
    for block in re.findall(r"<figure.*?</figure>", html, re.S):
        found = re.search(r'src="([a-z-]+)-thumb\.png"', block)
        if not found:
            continue
        printed[found.group(1)] = dict(
            re.findall(r"<dt>(\w+)</dt><dd>(.*?)</dd>", block, re.S))

    prints = fingerprints()
    assert set(printed) == set(prints), (
        f"the sheet and the corpus hold different fixtures: "
        f"{set(printed) ^ set(prints)}")
    import html as unescape

    stale = {
        slug: {axis: (was, prints[slug].values[axis])
               for axis, was in values.items()
               if unescape.unescape(was) != prints[slug].values.get(axis)}
        for slug, values in printed.items()}
    stale = {slug: moved for slug, moved in stale.items() if moved}
    assert not stale, (
        f"the committed sheet is older than the corpus — {sorted(stale)} "
        f"moved since it was captured: {stale}. Regenerate it with "
        f"tools/contact_sheet.py before reading anything off it.")


def test_the_blind_spot_cleared_and_the_labels_went_degenerate():
    """Phase 0: the axis-two blind spot WAS a labelling artefact, and clearing
    it exposed a worse problem than the one it solved.

    `agreement.unreachable()` reports zero. It reported two, and both traced to
    a pair of verdicts that could not both be right — one called two pages the
    same site because only the lettering changed, the other called two pages
    two studios for the same reason. `pairs.json` names colour and subject and
    was silent on type setting; the rule was written into it before the
    verdicts were looked at, and it moved exactly one.

    So axis two's justification is gone. It was built to close this blind spot
    and the blind spot was never evidence about axes.

    AND THE LABELS ARE NOW A PURE FUNCTION OF `first_screen` — all thirteen of
    them. That is not a coincidence and it is the finding that matters: with
    colour, subject and type setting all discounted by the judging rules, the
    only arrangement the generator can vary is which of five first screens it
    opens on. A fold verdict has nothing else to rest on.

    Labels that restate one axis measure self-consistency, not validity, which
    is the contamination `pairs.json` was rewritten once to escape — arriving
    this time through the back door, not through vocabulary. Until the corpus
    has a SECOND arrangement dimension, agreement cannot validate anything, and
    that is the evidenced case for page architecture as the next axis.

    This test pins both halves. If a later axis breaks the degeneracy, this
    fails and should — say so in the commit that breaks it.
    """
    prints = fingerprints()
    slugs = sorted(prints)
    moved = {(a, b): prints[a].differs_from(prints[b])
             for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    assert agreement.unreachable(moved) == []

    determined = sum(
        1 for row in agreement.load()
        if ((prints[row["a"]].values["first_screen"]
             == prints[row["b"]].values["first_screen"])
            == (row["verdict"] == "same")))
    assert determined == len(agreement.load()), (
        f"{determined} of {len(agreement.load())} verdicts are 'do they share "
        f"first_screen'. If this dropped, the corpus grew a second arrangement "
        f"dimension and agreement means something again — re-pin and say so")
