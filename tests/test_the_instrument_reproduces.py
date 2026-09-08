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
RULER = "575db030"
RULE = "624e27dc"
LABELS = "4f147671"
# The held-out third, frozen verbatim. It moves only when a pair is
# RETIRED, never when one is re-judged.
HELD_OUT = "a8c63664"
SAME_TRADE_MEAN = 0.70
# 19 of 33, and the drop from "40/40" is a correction rather than a regression.
# That score was taken against verdicts read off a contact sheet captured in a
# 720-pixel window — below the breakpoint where the split hero stacks and the
# columns collapse — of a corpus that had already moved underneath it. Two
# standing tests now hold the sheet to the corpus and the thumbnails to the
# desktop fold, the labels were re-judged blind against what actually ships,
# and this is what the vector scores when the pictures are the right ones.
#
# What it says: the pages a person calls one studio share a skeleton and a
# typeface and differ in colour, and the vector has no axis for the typeface
# and weights colour through `mood` at 2.0. That is the case for type
# treatment as axis two, and this number is what it has to move.
AGREEMENT = (19, 33)


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

    slugs = sorted(prints)
    same_trade = [fp.distance(prints[a], prints[b])
                  for i, a in enumerate(slugs) for b in slugs[i + 1:]
                  if trades[a] == trades[b]]
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
    assert same_pairs == ["dentist/law", "hvac/roofer", "threadbare/hvac"], (
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
    assert (held.ordered, held.comparisons) == (5, 5)
    assert (tuned.ordered, tuned.comparisons) == (6, 12)


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


def test_the_blind_spot_is_pinned_and_reweighting_cannot_close_it():
    """Three comparisons no weighting of the current axes can reach.

    A "same" pair that differs on a superset of a "different" pair's axes is
    further apart under any non-negative weights — exactly, with no threshold
    and no search. `hvac`/`roofer` is judged one site and differs on six axes;
    `contractor-bare`/`roofer` is judged two and differs on four of the same
    six. The two extra are `accent` and `hero_subject` — colour and subject,
    which the judging rule in `pairs.json` says cannot alone make a different
    site. The vector counts precisely what the judge discounts.

    Pinned because "agreement is 58%" invites re-weighting, and this says
    re-weighting is not the answer for these three. Searching two hundred
    thousand weightings reached 28/33 and only by zeroing three axes — a
    five-parameter fit on sixteen verdicts, which is the fitted threshold this
    project has already thrown out once.
    """
    prints = fingerprints()
    slugs = sorted(prints)
    moved = {(a, b): prints[a].differs_from(prints[b])
             for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    blind = agreement.unreachable(moved)
    assert len(blind) == 3, [f"{n} contains {f}" for n, f, _ in blind]
    assert {near for near, _, _ in blind} == {"hvac/roofer", "threadbare/hvac"}
