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
command per width and nothing here needs a driver. If this ever has to run on
a machine without Chrome, that is the moment to add it.
"""

from __future__ import annotations

import base64
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from app.adapters import photos as photos_api
from app.adapters.imageinfo import media_type_of
from app.core.config import google_places_api_key
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
CHROME = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Chromium.app/Contents/MacOS/Chromium",
          shutil.which("google-chrome") or "",
          shutil.which("chromium") or "")
# The second row is the one that decides. Above the fold is the only second
# that matters — it is what the owner sees when the laptop is turned around —
# and page architecture is mostly a below-the-fold property. If two sites are
# still indistinguishable in the first viewport after an axis is added, that
# axis was not doing the work.
WIDTHS = (("desktop", 1440, 1100), ("mobile", 390, 844),
          ("fold", 1440, 820))


def chrome() -> str | None:
    return next((path for path in CHROME if path and Path(path).exists()), None)


def shoot(binary: str, page: Path, out: Path, width: int, height: int) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [binary, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={width},{height}",
         f"--screenshot={out}", page.resolve().as_uri()],
        capture_output=True, timeout=60)
    return out.exists() and result.returncode == 0


def main() -> int:
    binary = chrome()
    if not binary:
        print("No Chrome or Chromium found. Install one, or add Playwright.",
              file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
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
            site_file.write_text(_inline_photographs(page, brief))
            shots = {}
            for label, width, height in WIDTHS:
                shot = OUT / f"{slug}-{label}.png"
                if shoot(binary, site_file, shot, width, height):
                    shots[label] = shot.name
            print(f"  {slug:16} {len(shots)} shot(s)")
            cards.append({
                "slug": slug,
                "name": brief.get("name") or slug,
                "trade": brief.get("trade") or "",
                "shots": shots,
                "page": site_file.name,
                "axes": fp.of(plan, spec, material_from_brief(brief)).as_row(),
            })

    cards = _closest_first(cards)
    (OUT / "index.html").write_text(_sheet(cards))
    (OUT / "fold.html").write_text(_sheet(cards, fold=True))
    print(f"\n  {OUT / 'index.html'}")
    print(f"  {OUT / 'fold.html'}   <- the first viewport, the one that decides")
    return 0


def _inline_photographs(page: str, brief: dict) -> str:
    """Embed the proxied photographs so the page stands alone.

    A generated page asks our own server for `/photo/<lead>/<n>`, and a
    screenshot taken from a file:// URL has no server to ask — so every
    photograph 404s and the capture is eleven grey rectangles. I nearly read a
    conclusion off exactly that: two law firms that looked identical because
    neither had loaded its hero.

    The bytes are already on disk, so they go in as data URIs. Slow and large,
    and it makes the sheet honest, which is the only thing it is for.
    """
    names = list(brief.get("place_photos") or [])
    key = google_places_api_key() or ""
    if not names or not key:
        return page

    cache: dict[str, str] = {}

    def replace(match: re.Match) -> str:
        index = int(match.group(1))
        if index >= len(names):
            return match.group(0)
        if index not in cache:
            data = photos_api.fetch(key, names[index],
                                    width=photos_api.MAX_WIDTH)
            kind = media_type_of(data) if data else None
            cache[index] = (
                f"data:{kind};base64,{base64.b64encode(data).decode()}"
                if data and kind else "")
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


def _sheet(cards: list[dict], *, fold: bool = False) -> str:
    e = html.escape
    shot = "fold" if fold else "desktop"
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
