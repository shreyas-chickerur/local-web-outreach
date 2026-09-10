"""Every heading, paragraph, list, image and fact a business published,
against whether it reached the generated page — and if not, which rule
dropped it, across the WHOLE corpus.

    .venv/bin/python tools/content_census.py

BRIEF §5, Slice D: "first, before changing anything." Pure measurement — no
model call, no write, replays every fixture's frozen direction the way
`tools/quality_census.py` does.

The measurement itself — `measure()`, and everything it depends on — lives
in `app.site.census`, not here, so a single lead's workspace screen and this
corpus-wide report call the identical function. This file only loops over
the fixtures and totals what comes back.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from app.site.census import FixtureCensus, measure
from app.site.pipeline import STAGES, run_stage
from app.store import db, leads

FIXTURES = Path("tests/fixtures/briefs")


def main() -> int:
    censuses: list[FixtureCensus] = []
    with db.session(":memory:") as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            slug = path.stem
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
            censuses.append(measure(conn, slug, lead_id))

    print(f"{len(censuses)} fixtures\n")
    for c in censuses:
        drops = c.dropped()
        if not drops:
            print(f"  {c.slug:20} everything published reached the page")
            continue
        print(f"  {c.slug}")
        for name, raw, reached, rule in drops:
            print(f"    {name:32} {reached:3}/{raw:<3}  {rule}")
        print()

    # Totals: share of raw items that reached the page, per field, across
    # the whole corpus — and which rule accounts for the most drops.
    totals: Counter[str] = Counter()
    reached_totals: Counter[str] = Counter()
    rule_drop_totals: Counter[str] = Counter()
    for c in censuses:
        for name, raw, reached, rule in c.rows:
            if "informational" in name:
                # A subset of another row already being totalled ("photos"),
                # printed per-fixture for diagnostic detail only. Summing it
                # into the grand total double-counts those photos — found
                # when this row started disappearing for fixtures whose own
                # photography began reaching the page (BRIEF §5) and the
                # OVERALL percentage moved for a reason unrelated to how
                # much material actually reached the page.
                continue
            base = re.sub(r"\s*\(.*\)$", "", name)
            totals[base] += raw
            reached_totals[base] += reached
            if raw > reached:
                # Group by the rule's own first clause, not its whole
                # sentence, so near-duplicate wording still totals together.
                key = rule.split(" — ")[0].split(": ", 1)[-1]
                rule_drop_totals[f"{base}: {key}"] += raw - reached

    print("=" * 72)
    print("TOTALS — share of published material that reached the page")
    print("=" * 72)
    grand_raw = grand_reached = 0
    for field_name in sorted(totals):
        raw, reached = totals[field_name], reached_totals[field_name]
        grand_raw += raw
        grand_reached += reached
        pct = reached / raw if raw else 1.0
        print(f"  {field_name:32} {reached:4}/{raw:<4}  {pct:.0%}")
    overall = grand_reached / grand_raw if grand_raw else 1.0
    print(f"  {'OVERALL':32} {grand_reached:4}/{grand_raw:<4}  {overall:.0%}")

    print()
    print("TOP RULES BY HOW MUCH THEY DROP")
    for key, count in rule_drop_totals.most_common(10):
        print(f"  {count:4}  {key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
