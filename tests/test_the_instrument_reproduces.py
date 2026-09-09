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
RULER = "d2f37ed7"
RULE = "95f4d93e"
LABELS = "edc76612"
# The held-out third, frozen verbatim. It moves only when a pair is
# RETIRED, never when one is re-judged.
HELD_OUT = "e3b0c442"
SAME_TRADE_MEAN = 0.5494
# Palette sampling — §2.2 — was offered to the identity call and the whole
# corpus re-decided under it (ruler and rule UNCHANGED: palette only widens
# the prompt, it does not touch an axis or a weight). All nineteen fixtures
# resolved through the model with no fallback and no claims-gate rejection.
#
# Checked carefully against the rendered output rather than against
# screenshots read at a glance — an earlier pass at this same check briefly
# misjudged `dentist`/`dentist-rich` as one studio from memory of an
# EARLIER rendering, corrected once the actual current markup was read.
# Every one of the ten pairs judged this round, including the three that
# were the strongest "same" verdicts before this redecide
# (`barbecue`/`barbecue-rich`, `roofer`/`roofer-rich`, and the trade trio
# built on `hvac-rich`), came back DIFFERENT. Zero same-trade pairs a
# stranger calls one studio, among the ten checked — stronger than the
# state before the corpus was widened, and agreement is 0 of 0 again for
# the same reason it was then: a rank needs at least one "same" pair.
AGREEMENT = (0, 0)


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
    assert len(same_trade) == 30, (
        f"{len(same_trade)} scored same-trade pairs, expected 30 — the corpus "
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


def test_there_are_no_inversions_because_there_is_nothing_to_invert():
    """An inversion is a "same" pair ranked further apart than a "different"
    one. With no "same" verdict anywhere in the corpus there can be none, and
    the empty list below says nothing about the vector — see
    `test_the_corpus_has_no_pair_a_stranger_calls_one_studio`."""
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    assert agreement.score(distances).inversions == []


def test_the_held_out_third_has_nothing_to_score_either():
    """It follows from there being no "same" verdict anywhere in the set.
    Agreement is a RANK — every pair called two studios must sit further apart
    than every pair called one studio — and with no pair called one studio
    there is nothing to rank, in the held-out third or out of it."""
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    held = agreement.score(distances, agreement.load(held_out=True))
    assert held.comparisons == 0


def test_the_corpus_has_no_pair_a_stranger_calls_one_studio():
    """§2's governing requirement, met on this corpus a second time and more
    strongly than the first.

    Ten pairs were checked after palette sampling (§2.2) was offered to the
    identity call and the whole corpus re-decided under it — including the
    three pairs that were this project's strongest "same" verdicts before
    the redecide: `barbecue`/`barbecue-rich` (identical on every axis),
    `roofer`/`roofer-rich`, and the trade trio that shared an opening, a
    treatment and a device across three colours. All three broke apart.
    Zero same-trade pairs read as one studio among the ten checked.

    The same-trade mean moved with it — 49% identical before this redecide,
    45% after — which is the primary claim this phase pre-registered, and it
    is not credited to palette sampling in isolation: the whole identity
    call was re-asked, and the diversity gate's retry-then-perturb sequence
    ran fresh for every fixture regardless of what the prompt added. What
    can be said is that offering a grounded colour candidate did not cost
    anything, and the corpus that resulted is more varied than the one
    before it.

    Agreement is 0 of 0 for the reason it was 0 of 0 before Phase 1 widened
    the corpus: a rank needs at least one "same" pair, and there is not one
    to rank against. The single-axis degeneracy check has nothing to check
    with zero "same" verdicts — any axis unique per fixture would explain
    all ten for free — so it is retired again rather than left asserting
    something vacuous. If a "same" verdict comes back, restore it.
    """
    verdicts = agreement.load()
    assert verdicts, "no verdicts at all"
    assert not [row for row in verdicts if row["verdict"] == "same"], (
        "a 'same' verdict is back — agreement can rank again")


SHEET = Path(".reviews/sheet/index.html")


def test_the_committed_sheet_shows_the_corpus_that_shipped():
    """The pictures a verdict is read off must be the pages that shipped.

    RESTORED. This guard was deleted by accident — a phase that rewrote the
    tail of this file truncated everything after the test it was replacing, and
    the suite went green because the guard was gone rather than because it
    passed. That is the defect this project keeps finding, committed by the
    person who wrote the tests for it, and the reason a deletion has to show up
    as a failure somewhere.

    The sheet was once captured nine minutes before the fixtures it shipped
    beside were re-frozen, so five of eleven pictures were of pages that no
    longer existed. The vector is printed under every thumbnail, so this is
    checkable. If it fails, regenerate the sheet — do not edit the captions.
    """
    import html as unescape
    import re

    assert SHEET.exists(), "no committed contact sheet to check"
    printed: dict[str, dict[str, str]] = {}
    for block in re.findall(r"<figure.*?</figure>", SHEET.read_text(), re.S):
        found = re.search(r'src="([a-z-]+)-thumb\.png"', block)
        if not found:
            continue
        printed[found.group(1)] = dict(
            re.findall(r"<dt>(\w+)</dt><dd>(.*?)</dd>", block, re.S))

    prints = fingerprints()
    assert set(printed) == set(prints), (
        f"the sheet and the corpus hold different fixtures: "
        f"{set(printed) ^ set(prints)}")
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
