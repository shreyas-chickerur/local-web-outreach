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
LABELS = "449b9ddb"
SAME_TRADE_MEAN = 0.52
AGREEMENT = (40, 40)


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


def test_the_standing_inversion_is_resolved_and_stays_resolved():
    """Pre-registered in .reviews/slice-b-predictions.md as the binding claim:
    after the first-screen contract lands, `dentist`/`law` resolves.

    It did — one chose `proof`, the other `facts`, which is the difference a
    person saw and the vector could not. Kept as a test so a later axis cannot
    quietly undo it while raising the mean."""
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    assert agreement.score(distances).inversions == [], (
        "an inversion came back — re-judge the pair blind before accepting it "
        "as noise, per .reviews/slice-b-predictions.md")
