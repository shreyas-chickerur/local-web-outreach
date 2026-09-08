"""What the fixtures actually produce, measured.

    .venv/bin/python tools/quality_census.py [--rebuild]

The headline number is the last one: the pairwise structural distance across
every fixture. If five different businesses produce pages more than about sixty
percent identical by fingerprint, the template ceiling is still there and no
amount of individual polish has moved it. Everything above that line is
diagnosis for when it is low.

Two things this asserts rather than reports:

* **A second pass must cost nothing.** Every model answer — the vision pass,
  the design direction — is persisted, so re-running the census re-asks
  nothing. If either re-asks, tuning the diversity budget over a few dozen
  leads is unaffordable and the loop is unusable. That is a failure, not a
  note.
* **The fingerprint comes from the decisions.** Never from the rendered page:
  hashing markup scores structurally identical sites as different because the
  businesses use different words, so the gate would pass everything while the
  numbers looked healthy.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from app.adapters import vision
from app.site import agreement
from app.site import fingerprint as fp
from app.site.opening import opening_spec
from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.render import (
    build_from_spec,
    hero_scores,
    material_from_brief,
    plan_for,
)
from app.site.theme import contrast, theme_for
from app.store import db, leads, sites

FIXTURES = Path("tests/fixtures/briefs")

# The measurement taken before Slice B, so progress is against a number rather
# than against a memory. Recorded here rather than in a note because the report
# should say whether it is better or worse every time it runs.
#
# 2026-09-08, eleven fixtures, NINE axes — type treatment added as axis two —
# weighted by visibility x decidedness (ruler 4616d461, gate rule a83a0283):
#
#   same-trade mean   51% distance  =  49% IDENTICAL   (7 scored pairs)
#   worst pair        44% distance  —  contractor-bare vs roofer
#   agreement         21 of 36
#
# NOT COMPARABLE to the 14 of 22 before it: different axes, different corpus,
# different labels. The number to read is the pre-registered claim, and it
# FAILED — `agreement.unreachable()` reports two, and the claim was zero.
#
# The mean went the wrong way too, 38% identical to 49%, and that is expected
# rather than excused: nine axes describe more difference than eight, so a
# ninth raises the mean for arithmetic reasons and the mean means less. This is
# why the claim was written about the blind spot instead.
#
# What the failure says, and it is the opposite of what the axis was for: the
# pairs a person calls one studio share their GEOMETRY and differ in type
# treatment, colour and subject — and the judge discounts all three. So the
# vector now carries a 2.5-weight term exactly where a person sees no
# difference, which is the failure mode `accent` and `hero_subject` already
# had. The axis is real and the corpus is more varied for it; as a term in the
# distance it currently makes the instrument worse. What that weight should be
# is the next fork, and it is not something to fit against thirteen verdicts.
#
# `threadbare` is excluded from every score — see `agreement.UNSCORED`.
BASELINE_SAME_TRADE = 0.51
# The closest same-trade pair, kept as a reading rather than as a target:
# it is judged DIFFERENT, and the pairs worth fixing are the inversions.
BASELINE_WORST = ("contractor-bare", "roofer", 0.44)
# Which ruler the numbers above were taken with. A distance is comparable only
# to another taken the same way, and comparing across a change of ruler has
# already produced two false readings — a corpus that changed under a pinned
# baseline, and a distance that became weighted while the baseline stayed flat.
BASELINE_METRIC = "4616d461"
# And which gate rule the corpus was decided under. Every frozen
# direction is an answer this rule accepted, so a baseline taken under
# one rule is not comparable to a corpus decided under another.
BASELINE_RULE = "a83a0283"
# And which judgements the agreement figure was taken against — the labels are
# as much a part of the ruler as the weights, and they were re-judged blind.
BASELINE_LABELS = "7e49403b"
# What it was, so a reader can see that the agreement figure crossed a
# change of labels rather than falling. "40 of 40" was scored against
# 449b9ddb, taken from contact-sheet thumbnails of a corpus that had
# moved, captured below the breakpoint where the layout changes.
BASELINE_LABELS_WAS = ("371f24fa", "14 of 22")
# True on the commit that re-pins, false on every commit after. Without
# it the first run under a new ruler always prints "no better than the
# baseline" — because the baseline IS that run's own measurement copied
# into a constant, and a self-comparison reads exactly like a confirmed
# unchanged result.
BASELINE_IS_FRESH = True

# One database on disk, shared by every tool that runs the fixtures.
#
# An in-memory database per tool meant the contact sheet paid for a full vision
# pass and then the census paid for another one, which makes the "a second pass
# costs nothing" guarantee true within a run and false between them — and the
# loop these tools exist to make cheap is the loop across them.
#
# Gitignored: it is a cache, and deleting it costs one rebuild.
FIXTURE_DB = Path("artifacts/fixtures.db")



class Counter:
    """How many times the model was asked, for the assertions below."""

    def __init__(self) -> None:
        self.vision = 0
        self.direction = 0

    def install(self) -> None:
        real_look, real_open = vision.look, opening_spec

        def counted_look(urls, place_photos=(), **kw):
            answer = real_look(urls, place_photos, **kw)
            if answer:
                self.vision += 1
            return answer

        vision.look = counted_look                              # type: ignore[assignment]

        import app.site.opening as opening
        import app.site.pipeline as pipeline

        def counted_open(brief, **kw):
            answer = real_open(brief, **kw)
            # Count model calls, not invocations. A frozen brief replays its
            # direction and never reaches the API, and counting the call made
            # the census report eleven questions it had not asked.
            if answer.get("read_by") == "claude":
                self.direction += 1
            return answer

        # At the source, and only at the source. `identity.decide` imports
        # `opening_spec` from `app.site.opening` directly, so patching the
        # pipeline's alias missed every call the diversity gate made and the
        # census reported zero. The alias is gone; one binding, one patch.
        opening.opening_spec = counted_open                     # type: ignore[assignment]
        pipeline.vision.look = counted_look                     # type: ignore[assignment]


def load(conn) -> dict[str, int]:
    """Every fixture as a lead, so the real pipeline runs against them."""
    ids: dict[str, int] = {}
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text())
        ids[path.stem] = leads.save_brief(conn, payload)
    return ids


def worst_contrast(page: str, theme) -> tuple[str, float]:
    """The tightest ground/ink pair the page actually renders."""
    worst = ("none", 21.0)
    for ground, ink in re.findall(
            r"--on-(\w+):\s*(#[0-9a-fA-F]{3,6})", page):
        pair = getattr(theme, ground if ground != "base" else "bg", None)
        if not pair:
            continue
        ratio = contrast(ink, pair)
        if ratio < worst[1]:
            worst = (f"{ink} on {ground}", ratio)
    return worst


def measure(conn, slug: str, lead_id: int) -> dict:
    brief = leads.brief_with_overrides(conn, lead_id)
    material = material_from_brief(brief)
    stored = sites.recall_stage(conn, lead_id, "direction") or {}
    config = dict(stored.get("config") or {})
    spec = spec_from_config(config)
    plan = plan_for(brief, spec)
    page = build_from_spec(brief, spec)
    theme = theme_for(spec.mood, spec.accent)

    published = brief.get("published") or {}
    source_blocks = list(published.get("blocks") or [])
    used = sum(1 for b in source_blocks
               if str(b.get("heading", ""))[:40] and
               str(b.get("heading", ""))[:40] in page)

    scores = hero_scores(material.images, material.photo_labels,
                         material.trade_kind, material.size_of,
                         material.photo_vision)
    return {
        "slug": slug,
        "trade": brief.get("trade"),
        "sections": [s.key for s in plan.sections],
        "available": len(plan.sections) + len(plan.dropped),
        "blocks_used": f"{used}/{len(source_blocks)}",
        "hero": plan.hero_photo,
        "hero_score": scores[0].total if scores else 0.0,
        "hero_why": scores[0].reasons if scores else {},
        "worst_contrast": worst_contrast(page, theme),
        "weight_kb": round(len(page.encode()) / 1024, 1),
        "signature": "-",              # Slice B
        "fingerprint": fp.of(plan, spec, material),
        "rationale": str(config.get("rationale") or "")[:110],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true",
                        help="discard stored answers and ask the model again")
    args = parser.parse_args()

    counter = Counter()
    counter.install()
    rows: list[dict] = []
    with db.session(FIXTURE_DB) as conn:
        ids = load(conn)
        for slug, lead_id in ids.items():
            if args.rebuild:
                sites.forget_stages(conn, lead_id)
            for stage in STAGES:
                try:
                    run_stage(conn, lead_id, stage)
                except Exception as exc:                        # noqa: BLE001
                    print(f"  {slug:16} FAILED at {stage}: {exc}",
                          file=sys.stderr)
                    break
            else:
                rows.append(measure(conn, slug, lead_id))

        first_pass = (counter.vision, counter.direction)

        # The assertion, not an observation: a second pass over a lead that
        # FINISHED must ask nothing. A lead that failed is excluded on
        # purpose — retrying a stage that never produced an answer is the
        # behaviour we want, not a caching leak, and counting it as one would
        # make the assertion fire on the wrong thing.
        finished = {row["slug"] for row in rows}
        for slug, lead_id in ids.items():
            if slug not in finished:
                continue
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
        again = (counter.vision - first_pass[0],
                 counter.direction - first_pass[1])

    _report(rows, first_pass, again)
    if again != (0, 0):
        print("\nFAIL: a second pass over a finished lead re-asked the model "
              f"(vision {again[0]}, direction {again[1]}). Every answer must "
              "be persisted or tuning the budget is unaffordable.",
              file=sys.stderr)
        return 1
    return 0


def _kind(trade) -> str:
    from app.site.render import trade_kind
    return trade_kind(trade)


def _report(rows, first_pass, again) -> None:
    print(f"\n{len(rows)} fixtures · model asked {first_pass[0]}× for "
          f"photographs, {first_pass[1]}× for direction · "
          f"second pass asked {again[0]} and {again[1]}\n")

    for row in rows:
        pair, ratio = row["worst_contrast"]
        print(f"  {row['slug']:16} {str(row['trade'])[:22]:24}"
              f" {len(row['sections']):2}/{row['available']:<2} sections"
              f"  blocks {row['blocks_used']:>6}"
              f"  {row['weight_kb']:>6}kB"
              f"  contrast {ratio:4.1f}")
        print(f"                   hero {row['hero']} "
              f"({row['hero_score']:+.2f})")
        if row["rationale"]:
            print(f"                   {row['rationale']}")

    # Every axis, derived from `fp.AXES` rather than listed. The list here had
    # gone stale twice over: it still named `layout_bias`, which stopped being
    # an axis, and it omitted `first_screen`, which weighs 2.5 — the heaviest
    # in the table and the one that had just landed. A reader could not
    # reconcile the printed vectors with the distances below them.
    long_axes = ("section_order", "compositions")
    short_axes = [axis for axis in fp.AXES if axis not in long_axes]
    print("\n  fingerprints")
    for row in rows:
        values = row["fingerprint"].values
        print(f"    {row['slug']:16} "
              + " ".join(f"{axis}={values.get(axis, '-')}"
                         for axis in short_axes))
        for axis in long_axes:
            print(f"    {'':16} {axis}={values.get(axis, '-')}")

    prints = [r["fingerprint"] for r in rows]
    slugs = [r["slug"] for r in rows]
    distances = {(slugs[i], slugs[j]): fp.distance(a, b)
                 for i, a in enumerate(prints)
                 for j, b in enumerate(prints) if i < j}
    print()
    # The inversion list prints with the rate, always. "Worse" has to be
    # inspectable rather than a single number with an explanation attached —
    # see .reviews/slice-b-predictions.md.
    read = agreement.score(distances)
    print(read.report())
    # The same guard the distance baseline has. "19 of 33" against a pinned
    # "40 of 40" reads as a collapse and is not a comparison at all when the
    # verdicts underneath have been re-judged or the scored set has changed.
    if agreement.labels_version() != BASELINE_LABELS:
        print(f"    NOT COMPARABLE to the pinned reading — that was scored "
              f"against labels {BASELINE_LABELS} and these are "
              f"{agreement.labels_version()}. A verdict describes a rendering, "
              f"so re-deciding the corpus re-takes the labels; re-pin rather "
              f"than reading the difference as a regression.")
    if BASELINE_IS_FRESH:
        was, reading = BASELINE_LABELS_WAS
        print(f"    FRESHLY RE-PINNED. The previous reading of \"{reading}\" "
              f"was scored against labels {was} — a different set of verdicts, "
              f"so this is not that number having fallen. It is the first "
              f"reading of a new one.")
    if agreement.UNSCORED:
        print(f"    {', '.join(sorted(agreement.UNSCORED))} excluded from "
              f"every score — no design to compare, only an absence. See "
              f"agreement.UNSCORED.")
    pairs = [(fp.distance(a, b), rows[i]["slug"], rows[j]["slug"])
             for i, a in enumerate(prints)
             for j, b in enumerate(prints) if i < j]
    if not pairs:
        return
    average = sum(p[0] for p in pairs) / len(pairs)
    pairs.sort()
    print(f"\n  PAIRWISE DISTANCE  mean {average:.0%} "
          f"across {len(pairs)} pairs")

    # The mean flatters us. Two businesses in different trades publish
    # different material, so their section sets differ for reasons that have
    # nothing to do with design — and the fingerprint counts that as variety.
    # The requirement is about two businesses in the SAME trade on the same
    # street, so that is the number to read.
    kinds = {r["slug"]: _kind(r["trade"]) for r in rows}
    every = [p for p in pairs if kinds[p[1]] == kinds[p[2]]]
    same = [p for p in every
            if not {p[1], p[2]} & agreement.UNSCORED]
    if same:
        within = sum(p[0] for p in same) / len(same)
        moved = within - BASELINE_SAME_TRADE
        if fp.metric_version() != BASELINE_METRIC:
            verdict = (f"NOT COMPARABLE — the baseline was measured with "
                       f"ruler {BASELINE_METRIC} and this is "
                       f"{fp.metric_version()}. Re-pin it rather than reading "
                       f"the difference.")
        elif BASELINE_IS_FRESH:
            verdict = ("FRESHLY RE-PINNED — this run IS the baseline, so there "
                       "is nothing to compare yet. The next run is the first "
                       "that can say better or worse.")
        else:
            verdict = ("no better than the baseline" if abs(moved) < 0.01
                       else f"{abs(moved):.0%} "
                            f"{'better' if moved > 0 else 'WORSE'} "
                            f"than the baseline")
        print(f"  SAME TRADE         mean {within:.0%} distance "
              f"= {1 - within:.0%} identical, across {len(same)} pairs")
        if len(every) != len(same):
            loose = sum(p[0] for p in every) / len(every)
            print(f"                     ({1 - loose:.0%} identical across all "
                  f"{len(every)} pairs including "
                  f"{', '.join(sorted(agreement.UNSCORED))} — printed so the "
                  f"exclusion is visible, not so the better number is)")
        print(f"                     baseline {BASELINE_SAME_TRADE:.0%} "
              f"({1 - BASELINE_SAME_TRADE:.0%} identical) — {verdict}")
        print("                     <-- the number Slice B has to move")
        # The verdict rather than the distance rank. "The case B has to fix"
        # used to flag whichever pair scored closest, which is now
        # `contractor-bare`/`roofer` — a pair somebody judged DIFFERENT. The
        # case to fix is the inversion list above; this column just says what
        # was actually seen, where anybody looked.
        seen = {frozenset((p["a"], p["b"])): p["verdict"]
                for p in agreement.load()}
        for score, one, two in sorted(same)[:3]:
            verdict = seen.get(frozenset((one, two)))
            flag = f"  <-- judged {verdict.upper()}" if verdict else ""
            print(f"    {score:>5.0%}  {one} vs {two}{flag}")
        # What the gate would say about the corpus it produced, recomputed
        # here rather than asserted. A constant claiming the gate was off
        # outlived the commit that turned it on, and the census went on
        # printing it under the pair the gate had just moved.
        collided = [(one, two) for _, one, two in same
                    if fp.collisions(prints[[r["slug"] for r in rows].index(one)],
                                     [prints[[r["slug"] for r in rows].index(two)]],
                                     )]
        print(f"    (the diversity gate is ON — "
              f"{len(collided)} of {len(same)} same-trade pairs would collide"
              + (": " + ", ".join(f"{a}/{b}" for a, b in collided)
                 if collided else "") + ")")
    blind = agreement.unreachable(
        {(a, b): prints[[r["slug"] for r in rows].index(a)].differs_from(
            prints[[r["slug"] for r in rows].index(b)])
         for a in [r["slug"] for r in rows] for b in [r["slug"] for r in rows]
         if a < b})
    if blind:
        print(f"\n  BLIND SPOT  {len(blind)} comparison(s) no weighting can "
              f"reach — the 'same' pair differs on a superset of the "
              f"'different' pair's axes,")
        print("              so it is further apart under any weights. Only a "
              "new axis reaches these.")
        for near, far, extra in blind:
            print(f"    {near:24} (same) contains {far:24} (different) "
                  f"— extra: {', '.join(sorted(extra)) or 'nothing'}")
    print("\n  closest pairs — these are the ones that look like one tool:")
    for score, one, two in pairs[:5]:
        shared = set(fp.AXES) - prints[
            [r["slug"] for r in rows].index(one)].differs_from(
            prints[[r["slug"] for r in rows].index(two)])
        print(f"    {score:>5.0%}  {one:16} vs {two:16} "
              f"same on: {', '.join(sorted(shared))}")


if __name__ == "__main__":
    raise SystemExit(main())
