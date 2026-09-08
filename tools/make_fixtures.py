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
    from app.store import db, leads, photos

    with db.session(Path("artifacts/fixtures.db")) as conn:
        stored = leads.save_brief(conn, {**payload, "name": payload["name"]})
        try:
            run_stage(conn, stored, "photographs")
        except BuildFailed:
            pass
        payload["photo_labels"] = photos.labels_for(conn, stored)
        payload["photo_vision"] = photos.vision_for(conn, stored)
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
    args = parser.parse_args()
    refresh = args.refresh

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
        seen = freeze_vision(payload)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        published = payload.get("published") or {}
        print(f"  {slug:18} {payload.get('trade')!r:34} vision={seen:2} "
              f"site={'yes' if payload.get('website_url') else 'no ':3} "
              f"photos={len(payload.get('place_photos') or [])+len(published.get('photos') or [])} "
              f"blocks={len(published.get('blocks') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
