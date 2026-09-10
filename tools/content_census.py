"""Every heading, paragraph, list, image and fact a business published,
against whether it reached the generated page — and if not, which rule
dropped it.

    .venv/bin/python tools/content_census.py

BRIEF §5, Slice D: "first, before changing anything." Pure measurement — no
model call, no write, replays every fixture's frozen direction the way
`tools/quality_census.py` does. Fix what this exposes; this file only
counts.

Every number here is read off the actual pipeline (`material_from_brief`,
`plan_for`, `build_from_spec`, and the section builders' own caps), not
reimplemented — two copies of "how many services show" would drift the way
this project's own history keeps finding.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.site.density import calculate_density_signal
from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.render import (
    FEATURE_CAP,
    _fills_rows,
    build_from_spec,
    material_from_brief,
    plan_for,
)
from app.store import db, leads, sites

FIXTURES = Path("tests/fixtures/briefs")

# Block kinds a section builder actually reads. Anything else published as a
# block is dropped in full — checked against the real corpus below, not
# assumed; a kind absent from this set the FIRST time this ran would have
# been a silent, permanent loss with nothing here to say so.
_CONSUMED_KINDS = {"feature", "events", "press", "story", "award", "partners"}


@dataclass
class FixtureCensus:
    slug: str
    rows: list[tuple[str, int, int, str]] = field(default_factory=list)

    def add(self, field_name: str, raw: int, reached: int, rule: str) -> None:
        self.rows.append((field_name, raw, reached, rule))

    def dropped(self) -> list[tuple[str, int, int, str]]:
        return [r for r in self.rows if r[1] > r[2]]


def _facts_summary(brief: dict, material) -> list[tuple[str, int, int, str]]:
    """address/phone/hours: the only fields `material_from_brief` treats as
    facts with a confidence gate, rather than bulk published content."""
    facts = brief.get("facts") or []
    rows = []
    for name in ("address", "phone"):
        candidates = [f for f in facts if f.get("field") == name]
        if not candidates:
            continue
        trusted = any(f.get("confidence") in ("verified", "operator_verified")
                      and f.get("value") for f in candidates)
        reached = 1 if getattr(material, name) else 0
        rule = ("kept: at least one source was verified" if trusted else
                "dropped: no source for it was verified — "
                "material_from_brief only trusts confirmed facts")
        rows.append((f"fact:{name}", 1, reached, rule))

    hour_facts = [f for f in facts if f.get("field") == "hours"]
    published_hours = bool((brief.get("published") or {}).get("hours"))
    if hour_facts:
        if published_hours:
            rows.append(("fact:hours", 1, 0,
                        "dropped: published.hours already had entries — the "
                        "hours FACT is only a fallback and is never "
                        "consulted when the scrape already found hours"))
        else:
            trusted = any(f.get("confidence") in ("verified", "operator_verified")
                          for f in hour_facts)
            rows.append(("fact:hours", 1, 1 if trusted else 0,
                        "kept: used as the fallback" if trusted else
                        "dropped: unverified and there was nothing to fall "
                        "back from"))
    return rows


def _blocks_summary(brief: dict, page: str) -> list[tuple[str, int, int, str]]:
    blocks = (brief.get("published") or {}).get("blocks") or []
    by_kind: dict[str, list[dict]] = {}
    for b in blocks:
        by_kind.setdefault(b.get("kind") or "", []).append(b)

    rows: list[tuple[str, int, int, str]] = []
    for kind, group in sorted(by_kind.items()):
        if kind not in _CONSUMED_KINDS:
            rows.append((f"block:{kind}", len(group), 0,
                        "dropped: no section builder reads this kind at all"))
            continue
        if kind in ("feature", "events", "press"):
            eligible = [b for b in group
                       if len((b.get("text") or "").split()) >= 18]
            short = len(group) - len(eligible)
            shown = min(len(eligible), FEATURE_CAP)
            reasons = []
            if short:
                reasons.append(f"{short} under the 18-word minimum")
            if len(eligible) > FEATURE_CAP:
                reasons.append(
                    f"{len(eligible) - FEATURE_CAP} beyond the "
                    f"{FEATURE_CAP}-block cap")
            rule = ("kept in full" if not reasons else
                    "dropped: " + ", ".join(reasons))
            rows.append((f"block:{kind}", len(group), shown, rule))
        else:
            # story / award / partners: each section reads exactly one
            # entry (`blocks_of(kind)[0]`), and `partners` additionally
            # needs >=3 entries in that one block to render at all.
            shown = 1 if group else 0
            if kind == "partners" and len(group[0].get("entries") or ()) < 3:
                shown = 0
                rule = "dropped: fewer than 3 entries in the block"
            elif len(group) > 1:
                rule = f"dropped: {len(group) - 1} more of this kind, only the first is read"
            else:
                rule = "kept" if shown else "dropped"
            rows.append((f"block:{kind}", len(group), shown, rule))
    return rows


def measure(conn, slug: str, lead_id: int) -> FixtureCensus:
    brief = leads.brief_with_overrides(conn, lead_id)
    stored = sites.recall_stage(conn, lead_id, "direction") or {}
    config = dict(stored.get("config") or {})
    spec = spec_from_config(config)
    plan = plan_for(brief, spec)
    page = build_from_spec(brief, spec)
    m = material_from_brief(brief)
    published = brief.get("published") or {}

    c = FixtureCensus(slug)

    for row in _facts_summary(brief, m):
        c.rows.append(row)

    # services + products: dense layout uses `_fills_rows`'s row-filling cap
    # (which can drop exactly one item to avoid a stranded row, not just
    # truncate at a ceiling); editorial layout (sparse counts) shows all of
    # them. `calculate_density_signal` is the same call `_services` makes.
    items = list(m.services) + list(m.products)
    if items:
        signal = calculate_density_signal(items)
        if signal["layout"] == "editorial":
            shown = len(items)
            rule = "kept in full — sparse layout shows every item"
        else:
            shown = _fills_rows(len(items))
            rule = ("kept in full" if shown == len(items) else
                    f"dropped: {len(items) - shown} to keep the grid's last "
                    f"row full (see render._fills_rows)")
        c.add("services+products", len(items), shown, rule)

    if m.menu_items:
        shown = min(len(m.menu_items), 24)
        rule = ("kept in full" if shown == len(m.menu_items) else
                f"dropped: {len(m.menu_items) - shown} beyond the 24-item cap")
        c.add("menu_items", len(m.menu_items), shown, rule)

    if m.quotes:
        shown = min(len(m.quotes), 6) if len(m.quotes) >= 2 else 0
        rule = ("dropped: fewer than 2 reviews, not worth a section"
                if len(m.quotes) < 2 else
                "kept in full" if shown == len(m.quotes) else
                f"dropped: {len(m.quotes) - shown} beyond the 6-card cap")
        c.add("reviews", len(m.quotes), shown, rule)

    if m.hours:
        shown = min(len(m.hours), 7)
        rule = ("kept in full" if shown == len(m.hours) else
                f"dropped: {len(m.hours) - shown} beyond the 7-line cap")
        c.add("hours_lines", len(m.hours), shown, rule)

    emails = published.get("emails") or []
    if emails:
        c.add("emails", len(emails), 1 if m.email else 0,
              "kept" if len(emails) == 1 else
              f"dropped: {len(emails) - 1} more — material_from_brief keeps "
              f"only the first")

    if m.socials:
        shown = min(len(m.socials), 4)
        rule = ("kept in full" if shown == len(m.socials) else
                f"dropped: {len(m.socials) - shown} beyond the 4-link cap")
        c.add("socials", len(m.socials), shown, rule)

    menu_media = published.get("menu_media") or []
    if menu_media:
        # `_menu()` reads only the first entry (BRIEF §5) — a link or an
        # embedded image, never invented structure from a document. Checked
        # against the real page, not assumed: this line used to hardcode
        # "no section builder reads this field at all" and stayed that way
        # after `_menu()` was fixed to read it, exactly the kind of drift a
        # second copy of "did this reach the page" always risks.
        first = menu_media[0]
        reached = 1 if first["url"] in page else 0
        rule = ("kept" if reached and len(menu_media) == 1 else
                "kept: the first; _menu() links to one document, not several"
                if reached else
                "dropped: not a food business, or no menu section built at all")
        c.add("menu_media", len(menu_media), reached, rule)

    # about vs a story block: `_about()` prefers `blocks_of("story")[0]` over
    # `published.about` outright — not a truncation, a full replacement.
    story_blocks = [b for b in (published.get("blocks") or [])
                    if b.get("kind") == "story"]
    if published.get("about"):
        if story_blocks:
            c.add("about_text", 1, 0,
                  "dropped: superseded by a 'story' block — _about() prefers "
                  "the block outright and never reads published.about when "
                  "one exists")
        else:
            c.add("about_text", 1, 1, "kept")

    for row in _blocks_summary(brief, page):
        c.rows.append(row)

    # Photographs: the pool is Google's place photos first, then the
    # business's own site photos (Material.images) — plan_for already
    # tracks exactly which never got spent by any section.
    pool = len(m.images)
    if pool:
        unused = len(plan.unused_images)
        used = pool - unused
        rule = ("kept in full" if unused == 0 else
                f"dropped: {unused} never spent by a hero, gallery, offer "
                f"card or feature block — pool exceeded every section's "
                f"capacity")
        c.add("photos", pool, used, rule)
        own_photos = len(published.get("photos") or [])
        place = len(brief.get("place_photos") or [])
        if own_photos and place:
            # Whether the business's OWN photography ever got a look-in, or
            # Google's photos (which sort first in the pool) filled every
            # slot before the pool reached them.
            own_urls = set(published.get("photos") or [])
            own_used = sum(1 for url in m.images
                           if url in own_urls and url not in plan.unused_images)
            if own_used == 0:
                c.add("own_site_photos (subset of photos, informational)",
                     own_photos, 0,
                     "dropped: Google's own photos filled every slot first "
                     "— none of this business's own site photography was "
                     "ever selected")

    return c


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
