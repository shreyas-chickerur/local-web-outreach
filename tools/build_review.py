"""The review bundle — what a person actually opens to form an opinion.

    .venv/bin/python tools/build_review.py
    open .reviews/review/index.html

Every fixture rendered standalone to `.reviews/review/<slug>.html`, an index
naming every business in plain English (trade, rating, why the page opens
the way it does, why the signature device is what it is — the model's own
words, never axis names), and `READ-ME-FIRST.md` saying what to look at,
what is weak, and what numbers not to trust.

PHOTOGRAPHS ARE COPIED, NEVER INLINED — the same correction
`tools/contact_sheet.py` got mid-session, applied here from the start rather
than repeated. A generated page asks our own server for `/photo/<lead>/<n>`;
copying the cached bytes into `.reviews/review/photos/` and rewriting the URL
to a relative path lets a file:// page load them with no server, for a
fraction of what inlining as base64 would cost. Unlike the contact sheet
(which links `.cache/photos` IN PLACE, since it is a throwaway, regenerated,
gitignored directory), this bundle COPIES: `.reviews/review/<slug>.html` is
meant to be committed and read stand-alone, and a relative path into a
gitignored cache outside its own directory would be dead the moment someone
else clones the repository. `.reviews/review/photos/` is itself gitignored
(see `.gitignore`) — a few hundred photographs are not history — but the
pages that reference them stay small and committed.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

from app.adapters import photos as photos_api
from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.render import build_from_spec, plan_for
from app.store import db, leads, sites

FIXTURES = Path("tests/fixtures/briefs")
OUT = Path(".reviews/review")
PHOTOS = OUT / "photos"
SHEET_THUMB = Path(".reviews/sheet")  # sibling directory, already committed


def _copy_photographs(page: str, brief: dict) -> str:
    """Copy the photographs this page needs into `PHOTOS`, and rewrite their
    URLs to a path relative to `OUT` — see the module docstring for why this
    copies rather than links in place, unlike `contact_sheet.py`."""
    names = list(brief.get("place_photos") or [])
    if not names:
        return page

    cache: dict[int, str] = {}

    def replace(match: re.Match) -> str:
        index = int(match.group(1))
        if index >= len(names):
            return match.group(0)
        if index not in cache:
            cached = photos_api._cache_path(names[index], photos_api.MAX_WIDTH)
            if not cached.exists():
                cache[index] = ""
            else:
                dest = PHOTOS / cached.name
                if not dest.exists():
                    shutil.copy(cached, dest)
                cache[index] = f"photos/{cached.name}"
        return cache[index] or match.group(0)

    lead_id = brief.get("lead_id")
    # `(?<![0-9A-Za-z])` — every LEGITIMATE occurrence of `/photo/<lead>/<n>`
    # is preceded by a quote, `&quot;`, or `, ` (a later entry in one
    # `srcset` list); the one occurrence that is not is inside the
    # og:image meta tag's ABSOLUTE URL (`app.site.render.absolute()`),
    # where it sits directly after the port number — `...8099/photo/1/6`.
    # Matching there ate the leading slash and glued the port to
    # `photos/<hash>.jpg` with nothing between them
    # (`...8099photos/<hash>.jpg`), on 17 of 19 committed pages. The
    # lookbehind excludes exactly that one case — a digit or letter
    # immediately before the match — without needing to enumerate every
    # legitimate preceding character.
    return re.sub(rf"(?<![0-9A-Za-z])/photo/{lead_id}/(\d+)(?:\?[^\s\"'&)]*)?",
                 replace, page)


def e(text: object) -> str:
    return html.escape(str(text or ""), quote=True)


def _card(slug: str, brief: dict, config: dict, plan) -> str:
    """One business, in plain English. Never an axis name."""
    trade = brief.get("trade") or "—"
    ratings = brief.get("ratings") or []
    rating = next((r for r in ratings if r.get("source") == "google"), None)
    stat = (f"{rating['value']} stars, {rating['reviews']} Google reviews"
            if rating else "no rating on file")

    rationale = str(config.get("rationale") or "").strip()
    signature = str(config.get("signature") or "none")
    signature_why = str(config.get("signature_why") or "").strip()

    name = brief.get("name") or slug
    thumb = SHEET_THUMB / f"{slug}-thumb.png"
    thumb_html = (f'<img class="thumb" src="../sheet/{e(slug)}-thumb.png" '
                  f'alt="{e(name)}" loading="lazy">' if thumb.exists() else
                  '<div class="thumb placeholder"></div>')

    device_line = (f'<p class="device"><b>The signature mark:</b> {e(signature_why)}</p>'
                  if signature != "none" and signature_why else "")

    return (
        f'<article class="card">'
        f'<a href="{e(slug)}.html">{thumb_html}</a>'
        f'<div class="body">'
        f'<h2><a href="{e(slug)}.html">{e(brief.get("name") or slug)}</a></h2>'
        f'<p class="meta">{e(trade)} &middot; {e(stat)}</p>'
        f'<p class="rationale">{e(rationale)}</p>'
        f'{device_line}'
        f'<p class="outline"><b>What is on the page:</b> {e(_plain_outline(plan))}</p>'
        f'</div></article>'
    )


def _plain_outline(plan) -> str:
    """`plan.outline()` without the layout/CTA header line, and with each
    section named by what it holds rather than its internal key — the
    outline is already free of axis vocabulary, this only drops the two
    lines that still read like debug output."""
    names = {
        "stats": "the numbers", "recognition": "an award",
        "credentials": "trust signals (licensed/insured, warranty, etc.)",
        "services": "what they offer", "menu": "the menu", "gallery": "photos",
        "about": "their own story", "features": "more from their site",
        "partners": "who they source from", "reviews": "reviews",
        "hours": "hours", "contact": "how to reach them",
    }
    bits = [names.get(s.key, s.key) for s in plan.sections]
    return ", ".join(bits) if bits else "nothing beyond the opening"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PHOTOS.mkdir(parents=True, exist_ok=True)

    cards: list[str] = []
    broken: list[str] = []
    for path in sorted(FIXTURES.glob("*.json")):
        slug = path.stem
        brief_raw = json.loads(path.read_text())
        # A fresh `:memory:` session per fixture, not the shared
        # `artifacts/fixtures.db` — that db's `build_state` cache holds
        # whatever a stage last actually computed, which for `direction` was
        # the live redecide itself (`read_by="claude"`, cached before the
        # fixture file was written back with its frozen decision). Reusing
        # it here would be reading a stale label, not a wrong answer, but a
        # reviewer bundle should prove the same thing
        # `test_the_instrument_reproduces.py` does: a clean checkout, no
        # cache, no network, replays every decision straight off the
        # committed fixture file. `read_by == "frozen"` is that proof.
        with db.session(":memory:") as conn:
            lead_id = leads.save_brief(conn, brief_raw)
            try:
                for stage in STAGES:
                    run_stage(conn, lead_id, stage)
            except Exception as exc:                            # noqa: BLE001
                print(f"  {slug:18} skipped: {exc}", file=sys.stderr)
                broken.append(slug)
                continue

            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            config = dict(stored.get("config") or {})
            if config.get("read_by") != "frozen":
                print(f"  {slug:18} did not replay a frozen direction",
                      file=sys.stderr)
                broken.append(slug)
                continue

            spec = spec_from_config(config)
            plan = plan_for(brief, spec)
            page = build_from_spec(brief, spec)
            page = _copy_photographs(page, brief)
            (OUT / f"{slug}.html").write_text(page)

            cards.append(_card(slug, brief, config, plan))
            print(f"  {slug:18} written")

    index = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Review — 19 generated sites</title><style>"
        "body{font-family:-apple-system,Segoe UI,sans-serif;max-width:1100px;"
        "margin:0 auto;padding:32px 20px;color:#1a1a1a;background:#faf8f4}"
        "h1{font-size:22px}.lede{color:#555;max-width:70ch}"
        ".card{display:flex;gap:20px;border:1px solid #ddd;border-radius:10px;"
        "padding:16px;margin:16px 0;background:#fff}"
        ".thumb{width:220px;height:auto;border-radius:6px;flex:none;"
        "object-fit:cover;aspect-ratio:16/10}"
        ".thumb.placeholder{background:#eee}"
        "h2{margin:0 0 4px;font-size:17px}h2 a{color:#1a1a1a;text-decoration:none}"
        ".meta{color:#777;font-size:13px;margin:0 0 10px}"
        ".rationale{margin:0 0 8px;font-size:14px;line-height:1.5}"
        ".device{margin:0 0 8px;font-size:13px;color:#444;font-style:italic}"
        ".outline{font-size:13px;color:#555}"
        "a{color:#8a3b1f}</style></head><body>"
        "<h1>Nineteen generated sites</h1>"
        "<p class=\"lede\">Each card is one business: what the model decided "
        "and why, in its own words, then a link to the standalone page. "
        "Start with <a href=\"READ-ME-FIRST.md\">READ-ME-FIRST.md</a> before "
        "reading anything into these.</p>"
        + "".join(cards) +
        "</body></html>"
    )
    (OUT / "index.html").write_text(index)

    print(f"\n  {len(cards)} written, {len(broken)} skipped")
    print(f"  {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
