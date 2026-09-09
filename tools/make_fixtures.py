"""Freeze real briefs as fixtures.

    .venv/bin/python tools/make_fixtures.py

The corpus every metric is measured against, and the corpus the diversity
budget is tuned on. Real businesses rather than invented ones, because the
failure this is all guarding against — five sites that look like they came from
one tool — only shows up across real variety: a restaurant with a rich site and
one with no site at all are different problems, and a roofer is a different
problem again.

Run once. The files are committed, so a metric that moves is the generator
changing rather than a directory listing changing underneath it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.cli import available_directories
from app.web.serialize import brief_to_dict
from app.workbench.brief import build_brief

OUT = Path("tests/fixtures/briefs")

# One per kind of problem, not one per trade we like.
WANTED: tuple[tuple[str, str, str], ...] = (
    ("restaurant-rich", "The Heritage Table", "Frisco, TX"),
    ("restaurant-bare", "Ichika", "Plano, TX"),
    ("barbecue", "Hutchins BBQ", "Frisco, TX"),
    ("roofer", "Status Roofing LLC", "Frisco, TX"),
    ("hvac", "Milestone Electric Air Plumbing", "Frisco, TX"),
    ("salon", "Salon Boutique", "Frisco, TX"),
    ("dentist", "Frisco Dental Care", "Frisco, TX"),
    ("law", "Snellings Law PLLC", "Frisco, TX"),
    # The hardest case in the corpus and the one the operator actually walks
    # into: a real business with a directory listing and nothing else.
    ("bare-trade", "Towson Law Firm, PLLC", "Frisco, TX"),
    # A contractor with no website at all: the highest-scoring prospect the
    # landing page produces, and the shape the operator actually walks into.
    # Nothing but a directory listing and ten photographs to build from.
    ("contractor-bare", "VIP PLUMBING EXPERTS LLC", "Plano, TX"),
    # Almost nothing, and what there is is poor: one photograph, no reviews.
    # If nothing in the corpus scores badly on vision, the type-led hero ships
    # untested — and that is the path tying Slice A to Slice B.
    ("threadbare", "S.Handyman", "Frisco, TX"),

    # Widening the corpus, 2026-09-08. The instrument ran out of businesses to
    # disagree about — judged whole-page after the signature device landed,
    # all twenty verdicts came back "different" and agreement went to 0 of 0.
    # Sameness is a same-TRADE problem (§2), so what is missing is not new
    # trades, it is a second and third business in the trades already here —
    # weighted toward the buckets that were already crowded, on purpose.

    # Second BBQ joint. Directly tests the pair the census has watched since
    # the diversity budget landed: barbecue vs. barbecue, not barbecue vs. a
    # restaurant that happens to serve food. If two smokehouses come out
    # looking alike, that is the real defect the mean is supposed to catch.
    ("barbecue-rich", "Hard Eight BBQ", "Coppell, TX"),
    # Fourth restaurant, a different register again: not fine dining, not a
    # smokehouse, not omakase — casual all-day counter service. Widens what
    # "restaurant" can mean in the corpus rather than deepening one shape of
    # it a fourth time.
    ("restaurant-casual", "Whisk Crepes Cafe", "Plano, TX"),
    # Second roofer, same city as the first. The pair Status Roofing has never
    # had to sit next to.
    ("roofer-rich", "Bert Roofing", "Dallas, TX"),
    # Second HVAC/plumbing outfit — a big regional chain rather than a small
    # shop, so the corpus has one of each register in a trade that currently
    # only has small operators.
    ("hvac-rich", "Legacy Plumbing", "Frisco, TX"),
    # Third in the same bucket, a different regional chain again. `trade_kind`
    # buckets Plumber/Roofing/General Contractor together, so this is the
    # fourth business landing in what was already the most crowded trade.
    ("hvac-second", "One Hour Air Conditioning & Heating", "Plano, TX"),
    # Second salon. `groom` had exactly one fixture, so every "same trade"
    # comparison in that bucket was structurally impossible until now.
    ("salon-rich", "Drybar", "Plano, TX"),
    # Second dentist, same reason: `care` had exactly one fixture.
    ("dentist-rich", "Plano Dental Loft", "Plano, TX"),
    # Third law firm. `desk` already had two (an attorney with a rich site and
    # one with none at all); this adds a third register to the same bucket
    # rather than leaving it at a pair.
    ("law-rich", "The Ammons Law Firm", "Frisco, TX"),
)


def _strip_fetched_html(payload: dict) -> None:
    """Drop the raw pages the fetcher held on to.

    `url_check` carries a `FetchResult`, and a `FetchResult` carries the whole
    downloaded page. One law firm's fixture was 610KB, 586KB of it HTML that
    nothing downstream reads — the extraction already happened, and `published`
    is its output. A fixture should be the evidence, not the transcript.
    """
    check = payload.get("url_check")
    if not isinstance(check, dict):
        return
    for key in ("result", "candidates"):
        value = check.get(key)
        for entry in (value if isinstance(value, list) else [value]):
            if isinstance(entry, dict) and "html" in entry:
                entry["html"] = ""


def freeze_vision(payload: dict) -> int:
    """Fold what the vision pass saw into the fixture itself.

    Without this a census run depends on `artifacts/fixtures.db`, which is
    uncommitted, so a clean clone measures a different system — `hero_subject`
    is constant, the hero scores change, and the fingerprints move. The ruler
    is versioned and its inputs were not, which makes the versioning worth
    less than it looks.

    Same class as the `published.photos` gap: the corpus differed from
    production in a way that hid the thing it exists to catch.
    """
    from app.site.pipeline import BuildFailed, run_stage
    from app.site.render import material_from_brief
    from app.store import db, leads, photos, sites

    with db.session(Path("artifacts/fixtures.db")) as conn:
        stored = leads.save_brief(conn, {**payload, "name": payload["name"]})
        try:
            run_stage(conn, stored, "photographs")
        except BuildFailed:
            pass
        # The design direction too, for the same reason. Without it a clean
        # checkout with no key measures a different system, and the pinned
        # baseline means nothing to anyone who was not here when it was taken.
        # Every stage, including `page`. The diversity gate compares against the
        # sites this workbench has generated, and that history is written when
        # a page is BUILT — so stopping at `direction` meant the gate never had
        # anything to compare against and never fired while freezing.
        direction_result: dict = {}
        page_result: dict = {}
        for stage in ("direction", "page"):
            try:
                result = run_stage(conn, stored, stage)
            except BuildFailed:
                break
            if stage == "direction":
                direction_result = result
            else:
                page_result = result
        # A REJECTION is not an exception — `_stage_page` returns
        # `{"rejected": True, ...}` rather than raising, because a rejection is
        # a result, not a crash. That silence is exactly what let this freeze:
        # the loop above finished normally, `direction` stayed persisted (it is
        # a separate stage from `page`), and nothing here checked whether the
        # PAGE built from that direction ever cleared the claims gate before
        # writing it into the fixture as if it had. Two real businesses whose
        # own site copy carries an unverifiable tenure claim ("Since 1945",
        # "45 years") got frozen with a `design_direction` the pipeline itself
        # never approved — and every fingerprint/census/agreement computation
        # in this project reads `design_direction` directly, none of them
        # re-checks the claims gate, so a rejected design measured as an
        # accepted one everywhere downstream.
        #
        # BRIEF §4: "No unverified fact ships... A rejection writes no
        # version, leaves the previous version live, is recorded." A fixture
        # is not a running site with a previous version to fall back to, so
        # there is nothing to leave live — the honest move is to refuse to
        # freeze it at all, the same as a `BuildFailed`.
        if page_result.get("rejected"):
            raise RuntimeError(
                f"page stage rejected — unsupported: "
                f"{page_result.get('findings')}. This business's own site "
                f"copy carries a claim the corroboration pipeline could not "
                f"verify. Pick a different business rather than freezing an "
                f"ungated direction.")
        direction = sites.recall_stage(conn, stored, "direction") or {}
        payload["design_direction"] = dict(direction.get("config") or {})
        payload["_gate_unresolved"] = bool(direction_result.get("unresolved"))
        # And the measurements, the last input that lived outside the corpus:
        # sizes come from `.cache/photos`, which is as uncommitted as the
        # fixture database was.
        material = material_from_brief(leads.brief_with_overrides(conn, stored))
        payload["photo_sizes"] = {
            url: list(size) for url in material.images
            if (size := material.size_of(url)) is not None}
        # Only what this brief's photographs actually are. Re-freezing under a
        # different lead id otherwise leaves the old keys behind, and stale
        # entries would mask a real mismatch rather than showing one.
        current = set(material.images)
        payload["photo_labels"] = {
            url: what for url, what in photos.labels_for(conn, stored).items()
            if url in current}
        payload["photo_vision"] = {
            url: what for url, what in photos.vision_for(conn, stored).items()
            if url in current}
        payload["photo_notes"] = {
            url: said["description"]
            for url, said in photos.described(conn, stored).items()
            if said.get("description")}
    return len(payload["photo_vision"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="re-research and re-freeze even if the file exists")
    parser.add_argument("--vision-only", action="store_true",
                        help="keep the researched brief, refold its vision "
                             "labels into it")
    parser.add_argument("--redecide", action="store_true",
                        help="keep the researched brief, throw away its frozen "
                             "design direction and decide it again under the "
                             "current gate")
    args = parser.parse_args()
    refresh = args.refresh

    if args.redecide:
        # A frozen direction replays and is never re-gated, which is right for
        # a build and wrong for a rule change: the corpus would go on
        # demonstrating a gate that no longer exists. So the answers are thrown
        # away and taken again, in slug order, against an empty history — the
        # order is part of the result and has to be reproducible.
        db_path = Path("artifacts/fixtures.db")
        db_path.unlink(missing_ok=True)
        for target in sorted(OUT.glob("*.json")):
            payload = json.loads(target.read_text())
            payload.pop("design_direction", None)
            try:
                seen = freeze_vision(payload)
            except RuntimeError as exc:
                print(f"  {target.stem:18} FAILED: {exc}", file=sys.stderr)
                continue
            target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            spec = payload.get("design_direction") or {}
            print(f"  {target.stem:18} vision={seen:2} "
                  f"first={spec.get('first_screen', '-'):6} "
                  f"mood={str(spec.get('mood', '-')):10} "
                  f"accent={str(spec.get('accent', '-')):10} "
                  f"read_by={spec.get('read_by', '-')}")
        return 0

    if args.vision_only:
        for target in sorted(OUT.glob("*.json")):
            payload = json.loads(target.read_text())
            seen = freeze_vision(payload)
            target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            print(f"  {target.stem:18} vision={seen}")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    directories = available_directories()
    for slug, name, where in WANTED:
        target = OUT / f"{slug}.json"
        if target.exists() and not refresh:
            print(f"  {slug:18} already frozen")
            continue
        try:
            brief = build_brief(name, location=where, directories=directories)
        except Exception as exc:                       # noqa: BLE001
            print(f"  {slug:18} FAILED: {exc}", file=sys.stderr)
            continue
        # `brief_to_dict`, not `dataclasses.asdict`: the server stores a lead
        # through this function, and it is not a straight dump — it maps the
        # extractor's `images` onto `photos`, which is the field the renderer
        # reads. Dumping the dataclass produced fixtures in a shape the product
        # never stores, so every fixture had zero of the business's own
        # photographs and the whole corpus measured a path that does not exist.
        payload = json.loads(json.dumps(brief_to_dict(brief), default=str))
        # The lead id is assigned by whichever database loads it, so a fixture
        # must not carry one — proxied photo URLs are built from it and would
        # otherwise point at somebody else's pictures.
        payload.pop("lead_id", None)
        _strip_fetched_html(payload)
        try:
            seen = freeze_vision(payload)
        except RuntimeError as exc:
            print(f"  {slug:18} FAILED: {exc}", file=sys.stderr)
            continue
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        published = payload.get("published") or {}
        flag = "  <-- UNRESOLVED COLLISION, see design_direction" \
            if payload.get("_gate_unresolved") else ""
        print(f"  {slug:18} {payload.get('trade')!r:34} vision={seen:2} "
              f"site={'yes' if payload.get('website_url') else 'no ':3} "
              f"photos={len(payload.get('place_photos') or [])+len(published.get('photos') or [])} "
              f"blocks={len(published.get('blocks') or [])}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
