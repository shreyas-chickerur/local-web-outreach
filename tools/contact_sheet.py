"""Every fixture, side by side, with what it decided printed underneath.

    .venv/bin/python tools/contact_sheet.py
    open artifacts/contact-sheet/index.html

The question this answers is not "is this page good". It is "do these look like
they came from five different studios", and that question can only be asked of
all of them at once. Keep it open while working on the generator.

The axis values sit under each screenshot on purpose: the picture tells you two
sites feel alike, and the vector tells you which axis collided. Without the
numbers you are left arguing about taste.

Headless Chrome rather than Playwright. Chrome is already on the machine and
Playwright would be 150MB of browsers to do the same job; the capture is one
command per width and nothing here needs a driver.

PHOTOGRAPHS ARE LINKED, NEVER INLINED. A generated page asks our own server
for `/photo/<lead>/<n>`, which a file:// capture cannot reach, so every page
written here has those URLs rewritten to a relative path into
`.cache/photos` — the same content-hashed files `app.adapters.photos` already
cached fetching them the first time, pointed at rather than re-encoded.
Inlining as base64 data URIs was tried first and reverted: it made a single
page (`roofer.html`) 105MB and the whole directory 731MB, which is not a
large file, it is several million tokens — the exact thing this project's own
`.reviews/` conventions warn against reading only part of. `artifacts/` is
gitignored regardless; regenerate on demand.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.adapters import photos as photos_api
from app.adapters.chrome_cdp import cdp_session as _cdp_session

# The DevTools plumbing (chrome() binary discovery, the WebSocket
# handshake/frame codec, the launch-Chrome-and-drive-it-over-CDP session)
# used to be defined here and re-imported into `tools/perf_census.py` — one
# real implementation, reached from a second place rather than copied.
# `app.adapters.chrome_cdp` is now that one implementation, reused a third
# time by `app.adapters.site_fetch.ChromeSiteFetcher`.
from app.adapters.chrome_cdp import chrome
from app.site import fingerprint as fp
from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.render import build_from_spec, material_from_brief, plan_for
from app.store import db, leads, sites

FIXTURES = Path("tests/fixtures/briefs")
# One database on disk, shared by every tool that runs the fixtures.
#
# An in-memory database per tool meant the contact sheet paid for a full vision
# pass and then the census paid for another one, which makes the "a second pass
# costs nothing" guarantee true within a run and false between them — and the
# loop these tools exist to make cheap is the loop across them.
#
# Gitignored: it is a cache, and deleting it costs one rebuild.
FIXTURE_DB = Path("artifacts/fixtures.db")

OUT = Path("artifacts/contact-sheet")
# The second row is the one that decides. Above the fold is the only second
# that matters — it is what the owner sees when the laptop is turned around —
# and page architecture is mostly a below-the-fold property. If two sites are
# still indistinguishable in the first viewport after an axis is added, that
# axis was not doing the work.
#
# (label, viewport width, viewport height, device scale). The scale shrinks the
# IMAGE without narrowing the PAGE, which is the distinction the committed row
# got wrong: `thumb` was captured in a 720-pixel window, so every thumbnail was
# a 720-pixel rendering rather than a half-size picture of the 1440 one. Below
# the 820 breakpoint the split hero stacks, the header changes and the columns
# collapse — so every blind verdict this project has taken was read off a
# layout the owner does not see when the laptop is turned around, while the
# caption said "half scale". Same viewport as `fold`, half the pixels.
WIDTHS = (("desktop", 1440, 1100, 1.0), ("mobile", 390, 844, 1.0),
          ("fold", 1440, 820, 1.0),
          # Small enough to commit regardless — this row is a PNG screenshot,
          # not a page, so it was never affected by how the pages themselves
          # link their photographs — still legible for the
          # only question the sheet asks.
          ("thumb", 1440, 820, 0.5),
          # THE WHOLE PAGE, which is what the ground truth is now judged from.
          # A fold picture cannot see an axis that lives below the fold: page
          # architecture rendered `ledger` byte-identical to `stacked` above it,
          # and its binding claim could not have passed however good the axis
          # was. Section edges and most of the signature device are down here
          # too. The fold row stays — first-screen axes still benefit from it —
          # and this is what a verdict describes.
          #
          # A tall window rather than a full-page flag, which headless Chrome
          # does not have. 6000 clears every fixture in the corpus; a page
          # longer than that would be cut, and `pages.html` shows the footer on
          # each one so that is visible rather than silent.
          ("page", 1440, 6000, 0.5))


# How many `shoot()` calls run at once. Each is an independent headless
# Chrome process writing to its own file — nothing shared, nothing to
# serialise. Six is comfortably under typical laptop core counts while still
# cutting a 95-shot run to a fraction of its serial time; raise it if the
# machine has room, but a named constant beats a number buried in a call site.
MAX_WORKERS = 6

# Which slug+width combinations have already been shot from the exact HTML
# they would be shot from again. Skipping a match is what makes iterating on
# one fixture cheap instead of re-paying for all nineteen every time.
MANIFEST = Path(".reviews/sheet/.captured.json")


# Chrome's headless `--screenshot` CLI mode silently clamps any requested
# `--window-size` width below this to exactly 500 CSS pixels — confirmed by
# measuring `window.innerWidth` from inside the page: 390, 450 and 500 all
# measured 500; 550 measured 550. Nothing in the CLI flags changes it
# (`--force-device-scale-factor` only affects the output image's pixel
# density, not the CSS layout width). This means the "mobile" width in
# `WIDTHS` below has NEVER actually rendered at 390px through `shoot()` —
# every "mobile" screenshot this project has taken, including the ones the
# sampled Slice G design review judged, was laid out for a viewport 110px
# wider than labelled, then cropped to 390px on output, which is exactly
# how a button that fits at a real 390px viewport reads as cropped in the
# capture (found chasing down a "duplicated CTA cropped at the mobile
# edge" finding that would not reproduce through any other means of
# checking the same page at the same width — see `.reviews/<phase>.md`).
CDP_MIN_WIDTH = 500


def _cdp_screenshot(binary: str, page: Path, out: Path, width: int, height: int,
                     scale: float = 1.0, timeout: float = 20.0) -> bool:
    """A screenshot below `CDP_MIN_WIDTH`, driven through the DevTools
    protocol rather than the `--screenshot` CLI flag — see `_cdp_session`."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with _cdp_session(binary, page, width, height, scale, timeout) as call:
        shot = call("Page.captureScreenshot", {"format": "png"})
        data = shot.get("result", {}).get("data")
        if not data:
            return False
        out.write_bytes(base64.b64decode(data))
    return out.exists()


def evaluate_in_page(binary: str, page: Path, width: int, height: int,
                      expression: str, scale: float = 1.0,
                      timeout: float = 20.0):
    """Run `expression` in the page at the given viewport and return its
    value — for measuring layout (bounding rects, `elementFromPoint`)
    directly rather than reading it back off a screenshot. Works at any
    width, including below `CDP_MIN_WIDTH`, since it always goes through
    `_cdp_session` rather than the CLI `--screenshot` flag."""
    with _cdp_session(binary, page, width, height, scale, timeout) as call:
        result = call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True})
        exception = result.get("result", {}).get("exceptionDetails")
        if exception:
            raise RuntimeError(f"evaluate failed: {exception}")
        return result.get("result", {}).get("result", {}).get("value")


def shoot(binary: str, page: Path, out: Path, width: int, height: int,
          scale: float = 1.0) -> bool:
    """One screenshot. Found NOT reproducible before this — the same file,
    shot twice in a row with no concurrency at all, came back byte-different
    roughly one time in three, and Phase 0's parallelisation was going to make
    that far more likely to bite rather than causing it.

    Two independent causes, both fixed:

    1. NO PROFILE ISOLATION. Without `--user-data-dir`, `--headless=new`
       launches against Chrome's real default profile — the one signed into
       whatever account this machine has, with its extensions and sync. The
       captured stderr showed real profile activity (`docs.google.com` and
       `mail.google.com` PWA-install checks) that has nothing to do with the
       page being screenshotted. A fresh, empty profile directory per call
       removes that entirely, and removes the risk of two concurrent
       invocations fighting over the same profile lock file, which
       `--headless=new` does not obviously serialise.
    2. NETWORK-DEPENDENT FONTS. Every generated page loads its font from
       `fonts.googleapis.com` with `display=swap` — render immediately in a
       fallback face, repaint once the real one downloads. Chrome's
       `--screenshot` fires on the load event, which can land before or after
       that repaint depending on how fast the network answers, so the exact
       same file can be captured mid-swap or post-swap. This is a form of
       exactly the failure this project's own fixtures were built to escape
       (`BRIEF`: "runs with no key, no cache and no network") — it just never
       applied to the SCREENSHOTS the fixtures were judged from, only to the
       data. `--host-resolver-rules` sends both font hosts to nowhere, so the
       request fails immediately and the fallback face is what renders,
       every time, with nothing to race against.

    A third cause, found chasing the second down: hero and card elements
    reveal on a CSS transition — `[data-reveal]` fades and rises in over up
    to a second, driven by a `reveals` class added late enough that a
    screenshot can land mid-transition. Respecting
    `prefers-reduced-motion` was already how the stylesheet turns that off —
    `--force-prefers-reduced-motion` just tells Chrome the visitor asked for
    it, which is a real, supported preference and not a hack around the page.

    `--user-data-dir` pointed at a fresh directory was tried first, for the
    same isolation reason profile activity showed up in captured stderr, and
    dropped: on this Chrome build a non-default profile directory made
    `--headless=new` hang on exit — the screenshot file appeared, correctly
    written, and the process then declined to die within the 60-second
    budget. Reproducibility does not need it: `--disable-background-networking`
    and its neighbours below stop the same profile activity from touching the
    render.

    Four repeats of the same file, same width, are now byte-identical, which
    is what a screenshot has to be before it can be trusted to prove anything
    about parallel vs. serial capture.

    Below `CDP_MIN_WIDTH` this dispatches to `_cdp_screenshot` instead — the
    CLI flag below cannot reach a genuine sub-500px viewport at all; see
    `CDP_MIN_WIDTH`'s comment.
    """
    if width < CDP_MIN_WIDTH:
        return _cdp_screenshot(binary, page, out, width, height, scale)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [binary, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--host-resolver-rules=MAP fonts.googleapis.com 127.0.0.1,"
         "MAP fonts.gstatic.com 127.0.0.1",
         "--disable-background-networking", "--disable-sync",
         "--disable-default-apps", "--disable-component-update",
         "--metrics-recording-only", "--no-default-browser-check",
         "--no-service-autorun", "--disable-features=Translate,OptimizationHints",
         "--force-prefers-reduced-motion",
         f"--window-size={width},{height}",
         f"--force-device-scale-factor={scale}",
         f"--screenshot={out}", page.resolve().as_uri()],
        capture_output=True, timeout=60)
    return out.exists() and result.returncode == 0


def _load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--widths", default=None,
        help="comma-separated subset of " + ", ".join(w[0] for w in WIDTHS)
             + " (default: all five). During iteration, 'page,fold' is enough "
               "— those are the two the ground truth is judged from; shoot "
               "all five only before a commit.")
    parser.add_argument(
        "--force", action="store_true",
        help="re-shoot even where the manifest says the HTML has not changed")
    args = parser.parse_args()

    wanted_names = (set(args.widths.split(",")) if args.widths
                    else {w[0] for w in WIDTHS})
    unknown = wanted_names - {w[0] for w in WIDTHS}
    if unknown:
        print(f"unknown width name(s): {sorted(unknown)}", file=sys.stderr)
        return 1
    widths = [w for w in WIDTHS if w[0] in wanted_names]

    binary = chrome()
    if not binary:
        print("No Chrome or Chromium found. Install one, or add Playwright.",
              file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    # Pass one: build every fixture's page and write its standalone HTML.
    # Sequential and cheap — string assembly and a replayed frozen direction,
    # not the thing Phase 0 measured as the bottleneck. Screenshots are.
    cards: list[dict] = []
    with db.session(FIXTURE_DB) as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            slug = path.stem
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            try:
                for stage in STAGES:
                    run_stage(conn, lead_id, stage)
            except Exception as exc:                            # noqa: BLE001
                print(f"  {slug:16} skipped: {exc}", file=sys.stderr)
                continue

            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            spec = spec_from_config(dict(stored.get("config") or {}))
            plan = plan_for(brief, spec)
            page = build_from_spec(brief, spec)

            site_file = OUT / f"{slug}.html"
            linked = _link_photographs(page, brief)
            site_file.write_text(linked)
            cards.append({
                "slug": slug,
                "name": brief.get("name") or slug,
                "trade": brief.get("trade") or "",
                "shots": {},
                "page": site_file.name,
                "axes": fp.of(plan, spec, material_from_brief(brief)).as_row(),
                # What the PNGs below are proved against: the manifest key is
                # this hash, not the file path, so a page that changed and one
                # that did not are told apart by content, never by name alone.
                "_html_hash": hashlib.sha256(linked.encode()).hexdigest(),
            })

    # Pass two: every (fixture, width) screenshot, shot in parallel. Each
    # `shoot()` call is one headless Chrome process writing to its own file —
    # nothing shared between them, nothing to serialise. Skipped when the
    # manifest already has this exact HTML hash for this width and the PNG is
    # still on disk; `--force` bypasses that.
    manifest = {} if args.force else _load_manifest()
    jobs: list[tuple[dict, str, int, int, float, Path]] = []
    skipped = 0
    for card in cards:
        for label, width, height, scale in widths:
            key = f"{card['slug']}:{label}"
            shot = OUT / f"{card['slug']}-{label}.png"
            if (not args.force and manifest.get(key) == card["_html_hash"]
                    and shot.exists()):
                card["shots"][label] = shot.name
                skipped += 1
                continue
            jobs.append((card, label, width, height, scale, shot))

    def run_one(job):
        card, label, width, height, scale, shot = job
        site_file = OUT / f"{card['slug']}.html"
        ok = shoot(binary, site_file, shot, width, height, scale)
        return card, label, shot, ok

    shot_count = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for card, label, shot, ok in pool.map(run_one, jobs):
            if ok:
                card["shots"][label] = shot.name
                manifest[f"{card['slug']}:{label}"] = card["_html_hash"]
                shot_count += 1

    for card in cards:
        card.pop("_html_hash", None)
        print(f"  {card['slug']:16} {len(card['shots'])} shot(s)")
    print(f"  ({shot_count} captured, {skipped} skipped — HTML unchanged "
          f"since the last capture)")
    _save_manifest(manifest)

    cards = _closest_first(cards)
    (OUT / "index.html").write_text(_sheet(cards))
    (OUT / "fold.html").write_text(_sheet(cards, fold=True))
    (OUT / "pages.html").write_text(_sheet(cards, fold=True, shot="page"))
    print(f"\n  {OUT / 'index.html'}")
    print(f"  {OUT / 'fold.html'}   <- the first viewport, the one that decides")

    # The committable copy: half-scale first viewports and the vectors, so a
    # reviewer reads the numbers from the branch rather than being told them.
    keep = Path(".reviews/sheet")
    keep.mkdir(parents=True, exist_ok=True)
    for card in cards:
        thumb = card["shots"].get("thumb")
        if thumb:
            shutil.copy(OUT / thumb, keep / thumb)
    (keep / "index.html").write_text(_sheet(cards, fold=True, shot="thumb"))
    # The whole-page row is NOT committed. It is what a verdict is judged from
    # now, and it is ten megabytes a run — on a directory that is rewritten
    # every time the corpus is re-decided, which is every axis. This repository
    # has already had a push fail on size once. The full-size sheets have never
    # been committed for the same reason; `pages.html` sits beside them in the
    # gitignored directory and the tool regenerates all of it deterministically.
    print(f"  {keep / 'index.html'}   <- committed beside the census")
    print(f"  {OUT / 'pages.html'}   <- the whole page, what a verdict judges")
    return 0


def _link_photographs(page: str, brief: dict) -> str:
    """Point the proxied photographs at the cached files, so the page stands
    alone without a server to ask.

    A generated page asks our own server for `/photo/<lead>/<n>`, and a
    screenshot taken from a file:// URL has no server to ask — so every
    photograph 404s and the capture is eleven grey rectangles. I nearly read a
    conclusion off exactly that: two law firms that looked identical because
    neither had loaded its hero.

    This USED to embed the bytes as base64 data URIs. That made a page like
    `roofer.html` 105MB and the whole `artifacts/contact-sheet` directory
    731MB — millions of tokens if anyone tried to read one, and the exact
    thing this project's own `.reviews/` handoffs warn against reading only
    part of. The bytes were already on disk in `.cache/photos` (content-hash
    named, `app.adapters.photos._cache_path`) the whole time; a file:// page
    can reach a relative path with no server just as well as it can reach a
    data URI, for a hundred-thousandth of the size. `MAX_WIDTH` is the same
    width `plan_for`/`build_from_spec` already fetched at, so the cache file
    this looks for is the one already on disk from building the page above —
    never fetched again here, only pointed at.
    """
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
            cache[index] = (
                os.path.relpath(cached, OUT) if cached.exists() else "")
        return cache[index] or match.group(0)

    lead_id = brief.get("lead_id")
    return re.sub(rf"/photo/{lead_id}/(\d+)(?:\?[^\s\"'&)]*)?", replace, page)


def _closest_first(cards: list[dict]) -> list[dict]:
    """The pair the fingerprint says is most alike, first and adjacent.

    The whole point of looking at this is to check the instrument. If two sites
    the vector calls identical also LOOK identical, the vector is measuring the
    right things and a gate can be built on it. If they look meaningfully
    different, the axis set is incomplete and the gate would be tuned against
    an instrument that does not work. That check is only possible with the two
    of them side by side.
    """
    prints = {card["slug"]: fp.Fingerprint(dict(card["axes"]))
              for card in cards}
    pairs = sorted(
        (len(prints[a["slug"]].differs_from(prints[b["slug"]])),
         a["slug"], b["slug"])
        for i, a in enumerate(cards) for b in cards[i + 1:])
    if not pairs:
        return cards
    _, one, two = pairs[0]
    lead = [c for c in cards if c["slug"] in (one, two)]
    rest = [c for c in cards if c["slug"] not in (one, two)]
    for card in lead:
        card["flag"] = (f"closest pair — {len(prints[one].differs_from(prints[two]))}"
                        f"/{len(fp.AXES)} axes apart")
    return lead + rest


def _sheet(cards: list[dict], *, fold: bool = False,
           shot: str | None = None) -> str:
    e = html.escape
    shot = shot or ("fold" if fold else "desktop")
    tiles = "\n".join(f'''
      <figure>
        <a href="{e(card['page'])}" target="_blank">
          <img src="{e(card['shots'].get(shot, ''))}" alt="">
        </a>
        {"" if fold else
          f'<img class="phone" src="{e(card["shots"].get("mobile", ""))}" alt="">'}
        <figcaption>
          <b>{e(card['name'])}</b> <span>{e(card['trade'])}</span>
          {f'<p class="flag">{e(card["flag"])}</p>' if card.get('flag') else ''}
          <dl>{''.join(f"<dt>{e(axis)}</dt><dd>{e(value)}</dd>"
                       for axis, value in card['axes'])}</dl>
        </figcaption>
      </figure>''' for card in cards)
    return f"""<!doctype html><meta charset="utf-8">
<title>Contact sheet — {len(cards)} fixtures</title>
<style>
 body{{margin:0;padding:28px;background:#111;color:#eee;
   font:13px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
 h1{{font-size:15px;font-weight:600;letter-spacing:.02em;margin:0 0 4px}}
 p.note{{color:#888;margin:0 0 24px;max-width:60ch}}
 .grid{{display:grid;gap:26px;
   grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}}
 figure{{margin:0;background:#1a1a1a;border:1px solid #2b2b2b;border-radius:10px;
   overflow:hidden}}
 figure > a > img{{display:block;width:100%;border-bottom:1px solid #2b2b2b}}
 img.phone{{display:block;width:38%;margin:10px auto 0;border:1px solid #333;
   border-radius:6px}}
 figcaption{{padding:12px 13px 14px}}
 figcaption b{{font-size:13.5px}}
 figcaption span{{color:#7a7a7a;margin-left:6px}}
 dl{{display:grid;grid-template-columns:auto 1fr;gap:1px 10px;margin:9px 0 0;
   font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px}}
 dt{{color:#6f6f6f}} dd{{margin:0;color:#c9c9c9;overflow-wrap:anywhere}}
 .flag{{margin:6px 0 0;color:#e08a5a;font-size:11px;font-weight:600}}
</style>
<h1>{len(cards)} fixtures{" — first viewport only" if fold else ""}</h1>
<p class="note">{"Above the fold is the only second that matters: it is what the "
 "owner sees when the laptop is turned around. If two of these are still "
 "indistinguishable here after an axis is added, that axis was not doing the "
 "work."
 if fold else
 "The question is not whether any one of these is good. It is whether a "
 "stranger would guess they came from the same tool. The vector under each "
 "screenshot says which axis collided when two of them feel alike."}</p>
<div class="grid">{tiles}</div>
"""


if __name__ == "__main__":
    raise SystemExit(main())
