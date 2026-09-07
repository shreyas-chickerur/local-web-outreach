"""Scoring the instrument against a person's eye.

The distance number cannot say whether an axis was worth adding: more axes
always means more room to differ, so a vector can get louder and less accurate
at once. Agreement with hand-judged pairs is what separates the two.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site import agreement

pytestmark = pytest.mark.unit

PAIRS = [
    {"a": "law", "b": "bare-trade", "verdict": "same"},
    {"a": "law", "b": "barbecue", "verdict": "different"},
    {"a": "salon", "b": "roofer", "verdict": "unsure"},
]


def test_the_vector_agreeing_with_the_eye_scores_full_marks():
    score = agreement.score(
        {("law", "bare-trade"): 0.12, ("law", "barbecue"): 0.88}, PAIRS)
    assert (score.agreed, score.judged) == (2, 2)
    assert score.rate == 1.0
    assert score.unsure == 1


def test_unsure_pairs_are_reported_and_never_scored():
    """Scoring against a coin flip adds noise, and those pairs are exactly
    where a second opinion is worth most."""
    score = agreement.score({("salon", "roofer"): 0.5}, PAIRS)
    assert score.judged == 0
    assert score.unsure == 1


def test_a_disagreement_names_the_pair_and_both_verdicts():
    """"Agreement went down" is not actionable. Which pair, and which way, is."""
    score = agreement.score(
        {("law", "bare-trade"): 0.90, ("law", "barbecue"): 0.90}, PAIRS)
    assert score.agreed == 1
    assert score.misses == [("law", "bare-trade", "same", 0.90)]
    assert "a person says same" in score.report()


def test_the_pair_order_does_not_matter():
    score = agreement.score({("bare-trade", "law"): 0.1}, PAIRS[:1])
    assert score.agreed == 1


def test_a_pair_with_no_measurement_is_skipped_not_counted_wrong():
    score = agreement.score({}, PAIRS)
    assert (score.agreed, score.judged) == (0, 0)


def test_more_axes_can_raise_the_number_while_agreement_falls():
    """The failure this metric exists to catch, stated as a test. Both pairs
    move further apart; the one a person called "same" crosses the line, so the
    instrument got louder and less accurate together."""
    before = agreement.score(
        {("law", "bare-trade"): 0.20, ("law", "barbecue"): 0.60}, PAIRS)
    after = agreement.score(
        {("law", "bare-trade"): 0.55, ("law", "barbecue"): 0.95}, PAIRS)
    mean_before = (0.20 + 0.60) / 2
    mean_after = (0.55 + 0.95) / 2
    assert mean_after > mean_before
    assert after.rate < before.rate


def test_the_committed_pairs_are_readable_and_name_real_fixtures():
    judged = agreement.load()
    assert len(judged) >= 10, "too few to say anything about the instrument"
    names = {p.stem for p in Path("tests/fixtures/briefs").glob("*.json")}
    for pair in judged:
        assert pair["verdict"] in ("same", "different", "unsure"), pair
        assert pair["a"] in names and pair["b"] in names, pair


def test_the_file_says_whose_judgement_it_is():
    """These are Claude's readings until Shreyas overwrites them, and a ground
    truth nobody can trace the provenance of is not a ground truth."""
    raw = json.loads(Path("tests/fixtures/pairs.json").read_text())
    why = " ".join(raw.get("_why") or [])
    assert "Claude" in why and "starting point" in why
