"""BRIEF §4's second invariant, held across the whole corpus: no rendered
page states a review count that contradicts the review count this system
independently corroborates from structured rating data.

`hvac` shipped both "over 20,000 5 star reviews" — verbatim from its own
published `about` text, so `render.unsupported()` correctly let it through,
since that check is about provenance (did they say this) and this was
their own words — and "6203", the corroborated Google review count
(`Material.reviews`), printed eight times on the same page. Both are real;
they contradict each other by roughly 3x, and nothing before this checked
a business's own numbers against each other. `app.site.contradiction.
reconcile()` drops the contradicting sentence from free text (`about`, and
each block's `text`) before it reaches any section builder — the copy
sentence is suppressed, never rewritten, and the corroborated number is
never touched. See `.reviews/slice-b-predictions.md` ("Round 3, Phase 1")
for the corpus-wide scan that found this was the only instance.

This is the standing version: not a test that this one string is gone, but
a test that holds the invariant itself, so a future section or block that
prints an uncorroborated review count fails here regardless of what it's
called or how it's built.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.site.contradiction import REVIEW_COUNT_RE as _REVIEW_COUNT_RE
from app.site.contradiction import contradicts as _contradicts

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")

# Imported, not copied (Phase 2, Step 3): this test reads the rendered
# PAGE, `app.site.contradiction` reads free text before it is rendered,
# and the two must agree on what counts as a contradiction or this test
# could pass for a reason unrelated to whether the fix actually works —
# a second copy of the same expression and tolerance could drift from
# the real one silently. This file used to carry that second copy.


def test_no_fixture_states_a_review_count_that_contradicts_the_corroborated_one():
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec, material_from_brief
    from app.store import db, leads, sites

    offenders: dict[str, list[str]] = {}
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
                f"numbers would be checked against a different system than "
                f"the one that pinned them")
            spec = spec_from_config(config)
            page = build_from_spec(brief, spec)
            material = material_from_brief(brief)
            if material.reviews is None:
                continue
            text = re.sub(r"<[^>]+>", " ", page)
            for match in _REVIEW_COUNT_RE.finditer(text):
                claimed = int(match.group("num").replace(",", ""))
                lower_bound = bool(match.group("bound") or match.group("plus"))
                if _contradicts(claimed, material.reviews, lower_bound):
                    offenders.setdefault(path.stem, []).append(match.group(0))

    assert not offenders, (
        f"these fixtures print a review count that contradicts the "
        f"corroborated one: {offenders}")


def test_the_hvac_fixture_specifically_no_longer_contradicts_itself():
    """The exact case that found the gap, held directly rather than only
    through the corpus-wide sweep above — so a change that happens to keep
    the sweep green cannot silently regress the fixture that motivated it."""
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec
    from app.store import db, leads, sites

    with db.session(":memory:") as conn:
        lead = leads.save_brief(
            conn, json.loads((FIXTURES / "hvac.json").read_text()))
        for stage in STAGES:
            run_stage(conn, lead, stage)
        brief = leads.brief_with_overrides(conn, lead)
        stored = sites.recall_stage(conn, lead, "direction") or {}
        spec = spec_from_config(dict(stored.get("config") or {}))
        page = build_from_spec(brief, spec)

    assert "6203" in page, "the corroborated review count should still print"
    assert "20,000" not in page, (
        "the contradicting claim from their own about text is still on "
        "the page")


# Phase 2c (`.reviews/NEXT-ROUND.md`): Phase 2b's own widened
# `REVIEW_COUNT_RE` read "N+" as an exact N, so a true FLOOR claim
# ("100+ Google reviews", corroborated 136) was dropped as if it
# contradicted the very count it is consistent with. Both directions,
# plus the case that motivated the widening in the first place, held
# together so a future change cannot fix one and reopen the other.
def test_a_lower_bound_review_count_below_the_corroborated_value_is_kept():
    assert not _contradicts(100, 136, lower_bound=True)


def test_a_lower_bound_review_count_far_above_the_corroborated_value_is_dropped():
    assert _contradicts(20000, 6203, lower_bound=True)


def test_over_n_reviews_still_drops_on_the_real_hvac_fixture():
    """The exact real-corpus case `contradicts()` was written for: hvac's
    own about text says "over 20,000 5 star reviews" against a
    corroborated 6,203 -- "over" is a floor claim too, and 20,000 sits
    far enough above 6,203 that it still contradicts."""
    import json as _json
    from pathlib import Path as _Path

    from app.site.contradiction import reconcile

    brief = _json.loads(_Path("tests/fixtures/briefs/hvac.json").read_text())
    about = brief["published"]["about"]
    assert "over 20,000 5 star reviews" in about
    assert "20,000" not in (reconcile(about, 6203) or "")


def test_review_count_re_reads_n_plus_over_and_more_than_as_a_lower_bound():
    for text in ("100+ Google reviews", "over 100 Google reviews",
                "more than 100 Google reviews"):
        match = _REVIEW_COUNT_RE.search(text)
        assert match, text
        assert match.group("num") == "100"
        assert match.group("bound") or match.group("plus"), (
            f"{text!r} should read as a lower-bound claim")
    match = _REVIEW_COUNT_RE.search("100 Google reviews")
    assert match and not (match.group("bound") or match.group("plus")), (
        "a bare count with no '+'/'over'/'more than' is an exact claim, "
        "not a floor")
