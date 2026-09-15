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
                claimed = int(match.group(1).replace(",", ""))
                if _contradicts(claimed, material.reviews):
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
