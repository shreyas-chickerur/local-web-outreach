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
RULER = "a762bcc9"
RULE = "254e171b"
LABELS = "122e6ec8"
# The held-out third, frozen verbatim. It moves only when a pair is
# RETIRED, never when one is re-judged.
HELD_OUT = "7aa64298"
SAME_TRADE_MEAN = 0.6152

# Round 4, Phase 3b (BRIEF §5, Slice G — rebuild the ground truth,
# `.reviews/slice-b-predictions.md`): the verdict set had sat at 0 live for
# two full rounds. Fifteen fresh verdicts, judged the same way the file's
# own header describes — whole page, scrolled top to bottom, blind, no axis
# values in view — from artifacts/contact-sheet/<slug>-page.png recaptured
# this same session, after every Phase 3a fix had landed. `threadbare`
# excluded from every pairing (`agreement.UNSCORED` — no design to compare,
# only an absence).
#
# Twelve of the fifteen landed in the held-out third by the hash
# (`is_held_out()`, computed on fixed pairings — some chosen because the
# census's own "closest pairs" list called them close, some for trade-mate
# coverage — never after seeing which way a verdict would land, which is
# the one thing choosing held-out membership would corrupt). Eleven of
# those twelve came back "different"; one, `roofer`/`hvac-rich`, came back
# "same" — an honest read, not a forced one: both pages open on the
# identical recipe (full-screen photograph, a rating number at display
# size in the corner, two buttons) and run the identical section SET
# below it (a band of three numbers, an eight-card service grid under the
# same heading, a review grid, a twelve-photo "Recent jobs" gallery, a
# two-column closing paragraph) — only the order of two of those sections
# swaps, plus one small extra badge row on one side.
#
# One "same" against eleven "different" is eleven held-out
# cross-comparisons — comfortably past the 4-5 asked for as a floor, not
# engineered to hit it: `barbecue`/`barbecue-rich`, the single closest
# same-trade pair the fingerprint has ever produced (17%, eight of twelve
# axes shared), was ALSO judged and ALSO came back "same" — but it landed
# in the tuning third by the same fixed hash, so it does not count toward
# the held-out score, whichever way that cuts.
#
# The result is not a clean pass. `roofer`/`hvac-rich` sits at 69% by the
# vector's own measure — nearly the corpus-wide mean of 80%, far closer to
# "apart" than "close" — yet a stranger reads it as the same design. Every
# inversion below traces to this one pair. Reported as found: a real,
# disclosed mismatch between the instrument and a stranger's eye on this
# specific pair, not explained away and not re-judged to make the number
# move.
# Round 3, Phase 3 (BRIEF §5, content census — acting on what it exposed,
# `.reviews/<phase>.md`):
#
# 3a. A business's own photography now sorts first in `Material.images`
# (was Google-first), and hero scoring carries a new, deliberately small
# `own_photo` term — `own_site_photos` measured 0 of 4 ever used before
# this; verified NO fingerprint value moved from this change alone (hero
# candidate quality gaps are real and the small bonus never overturns
# them) — content-only, confirmed by comparing every axis value before
# and after with nothing else touched.
# 3b. `menu_media` (a menu PDF or photograph, extracted and stored since
# Slice A but read by no section builder) now has one: `_menu()` links to
# it directly when there is no parsed `menu_items` to show, and appends it
# as a "see the whole menu" link when there is. Moves `section_order` for
# any fixture that had `menu_media` but no `menu_items` (`restaurant-rich`
# gained a `menu` section it never had).
# 3c. `block:feature`'s cap raised 4 -> 6 (`FEATURE_CAP`): checked what
# items 5+ actually were, fixture by fixture, before moving the number —
# some corpora are a genuine FAQ or service list cut off arbitrarily;
# fewer are testimonial- or hours-shaped blocks a scraper mis-filed as
# "feature", which start appearing around item 7 on the fixtures checked.
# 6 recovers most of the real loss without reaching that point. Content-
# only: no fingerprint value moved from the cap alone.
# 3d. A lone, uncontested Google Business Profile claim now verifies
# `address`/`phone` on its own (`app/workbench/corroborate.py`) — GBP
# listings are verified against the business by Google before they go
# live, a real if different kind of corroboration; scoped to exactly
# these two fields, not extended to others on the strength of two
# examples. Genuine conflicts between sources (12 of the corpus's 19
# dropped facts, more than the 7 lone-Google ones) are UNCHANGED — still
# never presented as fact. Moves `section_order` for any fixture that
# gained a `contact` section it did not have before (`bare-trade`,
# `contractor-bare`, `dentist-rich`, `threadbare`).
#
# 3b and 3d together re-decided the corpus (ruler and rule UNCHANGED — no
# weight or axis definition moved). Zero collisions on the first attempt,
# across all 171 pairs. Same-trade mean moved 56.10% -> 61.52%; the
# closest pair the corpus has ever produced is `barbecue`/`barbecue-rich`
# at 17% (eight of twelve axes shared) — reported here because BRIEF's own
# convention is to name the closest pair, not because it was judged: see
# below.
#
# Superseded by Phase 3b, above: agreement is no longer 0 of 0. Scored
# against every live verdict (tuning third included) rather than the
# held-out third alone — see `HELD_OUT_AGREEMENT` for the number that
# actually says something about generalisation.
AGREEMENT = (22, 26)
# The held-out third only — never used to choose a rule or a weighting,
# only to score one afterwards. This is the number Phase 3b's own binding
# claim was about.
HELD_OUT_AGREEMENT = (9, 11)


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


def test_every_inversion_traces_to_the_one_disputed_pair():
    """An inversion is a "same" pair ranked further apart than a "different"
    one. Phase 3b's fifteen verdicts produced two live "same" pairs, but only
    one of them — `roofer`/`hvac-rich` — sits far enough out (69%, close to
    the corpus-wide mean) to invert against anything; `barbecue`/
    `barbecue-rich`, the closer of the two "same" calls, inverts nothing.

    This is a real, disclosed mismatch reported as found, not a defect in the
    test: a stranger reads `roofer`/`hvac-rich` as one template (identical
    hero, identical section set, only two sections swapping order) and the
    vector reads it as nearly as far apart as any two unrelated businesses in
    the corpus. Pinned exactly rather than just counted, so a future change
    that resolves it — or quietly makes it worse — is visible here."""
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    inversions = agreement.score(distances).inversions
    same_pairs = {inv[0] for inv in inversions}
    assert same_pairs == {"roofer/hvac-rich"}, (
        f"a different pair is inverting now: {same_pairs}")
    assert len(inversions) == 4, inversions


def test_the_held_out_third_scores_past_the_floor_this_round_asked_for():
    """Agreement is a RANK — every pair called two studios must sit further
    apart than every pair called one studio. Phase 3b's binding claim was
    "enough pairs that the held-out third holds 4-5 scorable comparisons";
    eleven landed, not engineered to clear the floor but a consequence of
    judging real trade-mate pairs and having exactly one of them come back
    "same"."""
    prints = fingerprints()
    slugs = sorted(prints)
    distances = {(a, b): fp.distance(prints[a], prints[b])
                 for i, a in enumerate(slugs) for b in slugs[i + 1:]}
    held = agreement.score(distances, agreement.load(held_out=True))
    assert (held.ordered, held.comparisons) == HELD_OUT_AGREEMENT, held.report()
    assert held.comparisons >= 4, (
        "back below the floor Phase 3b's binding claim asked for")


def test_the_corpus_has_exactly_the_judged_same_pairs_this_round_found():
    """§2's governing requirement, RE-PROVEN this round rather than held by
    inaction — the state the two previous rounds' version of this test
    described (zero live verdicts) ended the moment Phase 3b judged fifteen
    pairs blind from whole pages.

    The requirement itself does not change: no pair a stranger calls one
    studio should exist uncaught. It is no longer vacuously true (there was
    nothing to catch) — it is now checked against something real, and the
    honest result is one disclosed exception, not a clean pass. Pinned to
    the EXACT set rather than merely "not empty", so a THIRD "same" verdict
    appearing — from a future judging round, or from someone editing this
    file by hand — is caught here rather than silently accepted as "expected,
    there's already one".
    """
    verdicts = agreement.load()
    same = {(row["a"], row["b"]) for row in verdicts if row["verdict"] == "same"}
    assert same == {("roofer", "hvac-rich"), ("barbecue-rich", "barbecue")}, (
        f"the live 'same' verdicts moved: {same}. If a judging round did "
        f"this on purpose, update the pinned set here and say why.")


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
