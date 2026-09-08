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

from app.adapters import claude, vision
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
# 2026-09-07, eleven fixtures, SEVEN axes (layout_bias removed as a duplicate
# of mood), weighted by visibility and decidedness (ruler 563eaa0b):
#
#   same-trade mean   52% distance  =  48% IDENTICAL
#   worst pair        27% distance  —  contractor-bare vs roofer, and
#                                      barbecue vs restaurant-rich
#
# An earlier baseline of 40% was taken against a nine-fixture corpus that was
# the wrong shape — no fixture carried the business's own photographs, so it
# was measuring a path the product does not have. Re-pinned rather than
# compared: a number that moved because the corpus changed is not progress, and
# leaving the old one in place would have reported 16% better on the day the
# fixtures were repaired.
#
# THE NUMBER IS NOT THE WHOLE STORY, and the contact sheet is why. The two
# attorneys now score 50% apart on this vector and are still, side by side,
# obviously the same page: same skeleton, same typeface pairing, same geometry,
# different photograph. So the vector currently OVERSTATES how different two
# sites are — the axes that would separate them (page architecture, type
# system, colour structure, section edges, the signature device) are exactly
# the ones Slice B adds and this file does not yet name.
#
# Which is the argument for the gate staying off. Gating on an instrument that
# reports 50% for two pages a stranger would call identical would reject builds
# for the wrong reasons and pass the ones that matter.
BASELINE_SAME_TRADE = 0.52
BASELINE_WORST = ("contractor-bare", "roofer", 0.27)
# Which ruler the numbers above were taken with. A distance is comparable only
# to another taken the same way, and comparing across a change of ruler has
# already produced two false readings — a corpus that changed under a pinned
# baseline, and a distance that became weighted while the baseline stayed flat.
BASELINE_METRIC = "563eaa0b"
# And which judgements the agreement figure was taken against — the labels are
# as much a part of the ruler as the weights, and they were re-judged blind.
BASELINE_LABELS = "747e4ef5"

# The gate is NOT on. With eight axes and four structural, "differ on four
# including one structural" fails almost everything the generator can currently
# produce — it would reject every build rather than improve any. The census
# reports the number; the gate turns on partway through Slice B, once the
# vector is wide enough for a site to satisfy it.
GATE_ENABLED = False
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
            if urls and claude.available():
                self.vision += 1
            return real_look(urls, place_photos, **kw)

        vision.look = counted_look                              # type: ignore[assignment]

        import app.site.pipeline as pipeline

        def counted_open(brief, **kw):
            self.direction += 1
            return real_open(brief, **kw)

        pipeline.opening_spec = counted_open                    # type: ignore[assignment]
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

    print("\n  fingerprints")
    for row in rows:
        values = " ".join(f"{k}={v}" for k, v in row["fingerprint"].as_row()
                          if k in ("mood", "accent", "layout_bias",
                                   "leads_with", "action"))
        print(f"    {row['slug']:16} {values}")

    prints = [r["fingerprint"] for r in rows]
    slugs = [r["slug"] for r in rows]
    distances = {(slugs[i], slugs[j]): fp.distance(a, b)
                 for i, a in enumerate(prints)
                 for j, b in enumerate(prints) if i < j}
    print()
    # The inversion list prints with the rate, always. "Worse" has to be
    # inspectable rather than a single number with an explanation attached —
    # see .reviews/slice-b-predictions.md.
    print(agreement.score(distances).report())
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
    same = [p for p in pairs if kinds[p[1]] == kinds[p[2]]]
    if same:
        within = sum(p[0] for p in same) / len(same)
        moved = within - BASELINE_SAME_TRADE
        if fp.metric_version() != BASELINE_METRIC:
            verdict = (f"NOT COMPARABLE — the baseline was measured with "
                       f"ruler {BASELINE_METRIC} and this is "
                       f"{fp.metric_version()}. Re-pin it rather than reading "
                       f"the difference.")
        else:
            verdict = ("no better than the baseline" if abs(moved) < 0.01
                       else f"{abs(moved):.0%} "
                            f"{'better' if moved > 0 else 'WORSE'} "
                            f"than the baseline")
        print(f"  SAME TRADE         mean {within:.0%} distance "
              f"= {1 - within:.0%} identical, across {len(same)} pairs")
        print(f"                     baseline {BASELINE_SAME_TRADE:.0%} "
              f"({1 - BASELINE_SAME_TRADE:.0%} identical) — {verdict}")
        print("                     <-- the number Slice B has to move")
        for score, one, two in sorted(same)[:3]:
            flag = ("  <-- the case B has to fix"
                    if {one, two} == set(BASELINE_WORST[:2]) else "")
            print(f"    {score:>5.0%}  {one} vs {two}{flag}")
        if not GATE_ENABLED:
            print("    (the diversity gate is off until the vector is wide "
                  "enough to satisfy it)")
    print("\n  closest pairs — these are the ones that look like one tool:")
    for score, one, two in pairs[:5]:
        shared = set(fp.AXES) - prints[
            [r["slug"] for r in rows].index(one)].differs_from(
            prints[[r["slug"] for r in rows].index(two)])
        print(f"    {score:>5.0%}  {one:16} vs {two:16} "
              f"same on: {', '.join(sorted(shared))}")


if __name__ == "__main__":
    raise SystemExit(main())
