"""Scoring the instrument against a person's eye.

The distance number cannot say whether an axis was worth adding: more axes
always means more room to differ, so a vector can get louder and less accurate
at once. Agreement with hand-judged pairs is what separates the two — and it is
scored by rank, because a threshold would be a free parameter fitted on the
same handful of pairs it is scored against.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site import agreement

pytestmark = pytest.mark.unit

PAIRS = [
    {"a": "law", "b": "bare-trade", "verdict": "same"},
    {"a": "law", "b": "roofer", "verdict": "different"},
    {"a": "salon", "b": "contractor-bare", "verdict": "different"},
    {"a": "barbecue", "b": "threadbare", "verdict": "unsure"},
]


def test_every_different_pair_further_apart_than_every_same_pair_is_perfect():
    score = agreement.score({
        ("law", "bare-trade"): 0.10,
        ("law", "roofer"): 0.70,
        ("salon", "contractor-bare"): 0.80,
    }, PAIRS)
    assert (score.ordered, score.comparisons) == (2, 2)
    assert score.rate == 1.0
    assert score.unsure == 1


def test_an_inversion_names_both_pairs_and_both_distances():
    """"Agreement went down" is not actionable. Which pair, which way, is."""
    score = agreement.score({
        ("law", "bare-trade"): 0.75,
        ("law", "roofer"): 0.70,
        ("salon", "contractor-bare"): 0.80,
    }, PAIRS)
    assert score.ordered == 1
    assert score.inversions == [("law/bare-trade", "law/roofer", 0.75, 0.70)]
    assert "should be closer than" in score.report()


def test_there_is_no_threshold_to_fit():
    """The metric must not have a knob that can be turned until the number
    looks good — that is the invalid baseline in another costume."""
    assert not hasattr(agreement, "SAME_BELOW")
    source = Path("app/site/agreement.py").read_text()
    assert "0.5" not in source and "0.50" not in source


def test_scaling_every_distance_cannot_change_the_score():
    """A rank metric reads the ordering, not the magnitudes — so a vector that
    simply got louder scores exactly the same."""
    quiet = {("law", "bare-trade"): 0.10, ("law", "roofer"): 0.30,
             ("salon", "contractor-bare"): 0.40}
    loud = {key: value * 2 for key, value in quiet.items()}
    assert agreement.score(quiet, PAIRS).rate == agreement.score(loud, PAIRS).rate


def test_unsure_pairs_are_reported_and_never_scored():
    score = agreement.score({("barbecue", "threadbare"): 0.5}, PAIRS)
    assert score.comparisons == 0
    assert score.unsure == 1


def test_the_pair_order_does_not_matter():
    score = agreement.score({
        ("bare-trade", "law"): 0.1, ("roofer", "law"): 0.9,
    }, PAIRS[:2])
    assert score.ordered == 1


def test_a_pair_with_no_measurement_is_counted_as_skipped_not_wrong():
    score = agreement.score({("law", "roofer"): 0.9}, PAIRS)
    assert score.unmeasured == 2
    assert score.comparisons == 0


def test_the_committed_labels_never_use_the_vector_s_own_vocabulary():
    """The contamination this file exists to prevent. A verdict justified in
    axis names is measuring the instrument against a restatement of itself."""
    axis_words = ("mood", "accent", "layout bias", "editorial", "structured",
                  "industrial", "refined", "leads with", "leads-with",
                  "stats-led", "gallery-led", "fingerprint", "axis")
    for pair in agreement.load():
        why = pair["why"].lower()
        used = [word for word in axis_words if word in why]
        assert not used, f"{pair['a']}/{pair['b']} justified by {used}: {why}"


def test_the_committed_pairs_are_readable_and_name_real_fixtures():
    judged = agreement.load()
    assert len(judged) >= 10, "too few to say anything about the instrument"
    names = {p.stem for p in Path("tests/fixtures/briefs").glob("*.json")}
    for pair in judged:
        assert pair["verdict"] in ("same", "different", "unsure"), pair
        assert pair["a"] in names and pair["b"] in names, pair


def test_the_file_says_whose_judgement_it_is_and_that_it_was_blind():
    raw = json.loads(Path("tests/fixtures/pairs.json").read_text())
    why = " ".join(raw.get("_why") or [])
    assert "Claude" in why and "BLIND" in why
