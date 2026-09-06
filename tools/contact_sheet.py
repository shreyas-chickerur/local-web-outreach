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

import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

from app.site import fingerprint as fp
from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.render import build_from_spec, material_from_brief, plan_for
from app.store import db, leads, sites

FIXTURES = Path("tests/fixtures/briefs")
OUT = Path("artifacts/contact-sheet")
CHROME = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Chromium.app/Contents/MacOS/Chromium",
          shutil.which("google-chrome") or "",
          shutil.which("chromium") or "")
WIDTHS = (("desktop", 1440, 1100), ("mobile", 390, 844))


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
    with db.session(":memory:") as conn:
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
            site_file.write_text(page)
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

    (OUT / "index.html").write_text(_sheet(cards))
    print(f"\n  {OUT / 'index.html'}")
    return 0


def _sheet(cards: list[dict]) -> str:
    e = html.escape
    tiles = "\n".join(f'''
      <figure>
        <a href="{e(card['page'])}" target="_blank">
          <img src="{e(card['shots'].get('desktop', ''))}" alt="">
        </a>
        <img class="phone" src="{e(card['shots'].get('mobile', ''))}" alt="">
        <figcaption>
          <b>{e(card['name'])}</b> <span>{e(card['trade'])}</span>
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
</style>
<h1>{len(cards)} fixtures</h1>
<p class="note">The question is not whether any one of these is good. It is
whether a stranger would guess they came from the same tool. The vector under
each screenshot says which axis collided when two of them feel alike.</p>
<div class="grid">{tiles}</div>
"""


if __name__ == "__main__":
    raise SystemExit(main())
