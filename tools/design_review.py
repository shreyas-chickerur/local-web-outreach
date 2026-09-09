"""Slice G, sampled — BRIEF §5: "screenshot at three widths, send with the
brief for a critique: defects only, closed categories."

    .venv/bin/python tools/design_review.py

Not the full slice. This is a cost-minimising first pass (BRIEF §5,
`.reviews/first-pass.md`): four fixtures, chosen for shape rather than at
random — one restaurant, one trade contractor, one professional practice,
and the threadbare fixture that has almost nothing to work with — at three
widths each. Twelve model calls, not the fifty-seven a full sweep over all
nineteen fixtures at three widths would cost. The question this answers is
narrower than "what does the review find": it is "does this instrument find
anything a person would also flag, and is a full sweep worth paying for".

One call per (fixture, width) screenshot, not one call per fixture bundling
all three — BRIEF's own phrase is "screenshot at three widths", plural
evidence for one verdict, but a review that mixes viewports in one prompt
cannot say which viewport a defect was seen at, and "which width" is exactly
the fact `contact_sheet.py`'s own fold-vs-page split exists to keep visible.

Categories are closed, per BRIEF: hierarchy, crop, spacing, colour, imagery,
credibility, and "reads as a template". A reviewer, not an author — this
finds defects, it does not fix them. Auto-repair of the deterministic ones
is its own fork, not attempted here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contact_sheet import (  # noqa: E402
    FIXTURE_DB,
    FIXTURES,
    OUT,
    _link_photographs,
    chrome,
    shoot,
)

from app.adapters import claude  # noqa: E402
from app.site.pipeline import STAGES, run_stage, spec_from_config  # noqa: E402
from app.site.render import build_from_spec  # noqa: E402
from app.store import db, leads, sites  # noqa: E402

# One restaurant, one trade contractor, one professional practice, and the
# fixture with almost nothing to work with — chosen for content shape, not
# sampled at random, so a finding can be read against why that fixture was
# picked.
SAMPLE = ("restaurant-rich", "hvac", "law", "threadbare")

WIDTHS = (("desktop", 1440, 1100, 1.0), ("mobile", 390, 844, 1.0),
          ("page", 1440, 6000, 0.5))

CATEGORIES = ("hierarchy", "crop", "spacing", "colour", "imagery",
              "credibility", "template")

SYSTEM = (
    "You are reviewing a screenshot of a generated small-business website. "
    "Report only real defects — a page with nothing wrong gets an empty "
    "list. Every finding must fall under exactly one of these categories: "
    "hierarchy (what draws the eye first is not what matters most), crop "
    "(a photograph cuts off a subject or face awkwardly), spacing "
    "(cramped, uneven, or colliding elements), colour (contrast, clash, or "
    "an accent used inconsistently), imagery (a photograph that is blurry, "
    "generic, or does not fit the business), credibility (something that "
    "reads as fake, templated boilerplate, or undermines trust), template "
    "(this looks like a generic template rather than a page built for this "
    "specific business). Do not invent a category outside this list.")


def _tool() -> dict:
    return {
        "name": "report_findings",
        "description": "Defects seen in this one screenshot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string",
                                         "enum": list(CATEGORIES)},
                            "description": {"type": "string"},
                        },
                        "required": ["category", "description"],
                    },
                },
            },
            "required": ["findings"],
        },
    }


def _review_one(slug: str, label: str, png: Path,
                 client: httpx.Client) -> list[dict]:
    data = png.read_bytes()
    blocks = [claude.image_block(data, "image/png")]
    try:
        answer = claude.structured(
            SYSTEM,
            f"This is the {label} viewport of a generated page for a "
            f"business ({slug}). List its defects, if any.",
            _tool(), client=client, blocks=blocks,
            max_tokens=1024, timeout=60.0)
    except claude.ClaudeError as exc:
        print(f"    {slug}:{label} — call failed: {exc}", file=sys.stderr)
        return []
    out = []
    for entry in answer.get("findings") or []:
        if not isinstance(entry, dict):
            continue
        category = entry.get("category")
        description = entry.get("description")
        if category in CATEGORIES and isinstance(description, str):
            out.append({"category": category, "description": description})
    return out


def main() -> int:
    if not claude.available():
        print("No ANTHROPIC_API_KEY — nothing to sample against.",
              file=sys.stderr)
        return 1
    binary = chrome()
    if not binary:
        print("No Chrome or Chromium found.", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    shots: dict[str, dict[str, Path]] = {}
    with db.session(FIXTURE_DB) as conn:
        for slug in SAMPLE:
            path = FIXTURES / f"{slug}.json"
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            spec = spec_from_config(dict(stored.get("config") or {}))
            page = build_from_spec(brief, spec)
            site_file = OUT / f"{slug}.html"
            site_file.write_text(_link_photographs(page, brief))

            shots[slug] = {}
            for label, width, height, scale in WIDTHS:
                out_png = OUT / f"{slug}-review-{label}.png"
                if shoot(binary, site_file, out_png, width, height, scale):
                    shots[slug][label] = out_png

    report: dict[str, dict[str, list[dict]]] = {}
    calls = 0
    with httpx.Client(timeout=60.0) as client:
        for slug in SAMPLE:
            report[slug] = {}
            for label, *_ in WIDTHS:
                png = shots.get(slug, {}).get(label)
                if not png:
                    continue
                report[slug][label] = _review_one(slug, label, png, client)
                calls += 1

    print(f"\n{calls} model calls, {len(SAMPLE)} fixtures x "
          f"{len(WIDTHS)} widths\n")
    total_findings = 0
    by_category: dict[str, int] = {}
    for slug, by_width in report.items():
        print(f"{slug}")
        for label, findings in by_width.items():
            if not findings:
                print(f"  {label:8} — no defects reported")
                continue
            print(f"  {label:8} — {len(findings)} finding(s)")
            for finding in findings:
                print(f"    [{finding['category']}] {finding['description']}")
                by_category[finding["category"]] = (
                    by_category.get(finding["category"], 0) + 1)
                total_findings += 1
        print()

    print(f"total: {total_findings} finding(s) across {calls} calls")
    if by_category:
        print("by category: " + ", ".join(
            f"{cat}={n}" for cat, n in
            sorted(by_category.items(), key=lambda kv: -kv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
