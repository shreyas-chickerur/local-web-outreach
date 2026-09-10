"""BRIEF §5 (Slice E), the capture problem, stated and answered: every
existing screenshot tool in this project passes
`--force-prefers-reduced-motion` (`tools/contact_sheet.py`'s own
docstring: found NOT reproducible without it, byte-different roughly one
time in three). A static capture of an animated page is one frame either
way — the question Slice E adds is how a PERSON actually sees the
motion, given every deterministic tool in this project is built to never
show it.

    .venv/bin/python tools/motion_preview.py [slug ...]

Answer: a SEPARATE tool, never used by the deterministic pipeline
(collision checks, design review, the committed contact sheet all keep
using `contact_sheet.shoot()` exactly as before — this file does not
touch it). A filmstrip of real frames, motion left ON, at fixed
intervals over the CSS cycle a `.hero-stills` backdrop actually runs
(16s per the `hero-still-cycle` keyframes in `app/site/styles.py`) —
enough frames to see the crossfade happen, not a full recording, since
the point is showing a person the choreography exists and looks right,
not archiving it.

Determinism is not a property this tool claims or needs: it is never
read by a test, a census, or a verdict. Human review only.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contact_sheet import (  # noqa: E402
    FIXTURE_DB,
    FIXTURES,
    OUT,
    _link_photographs,
    _ws_handshake,
    _ws_recv,
    _ws_send,
    chrome,
)

from app.site.pipeline import STAGES, run_stage, spec_from_config  # noqa: E402
from app.site.render import build_from_spec  # noqa: E402
from app.store import db, leads, sites  # noqa: E402

WIDTH, HEIGHT = 1440, 900
FRAME_COUNT = 6
FRAME_INTERVAL_S = 2.5   # 6 frames over 15s covers one 16s crossfade cycle
FILMSTRIP_DIR = Path("artifacts/motion-preview")


def capture_filmstrip(binary: str, page_path: Path, out_dir: Path) -> list[Path]:
    """`FRAME_COUNT` real screenshots, motion left on, at fixed intervals."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    with tempfile.TemporaryDirectory(prefix="motion-") as profile:
        proc = subprocess.Popen(
            [binary, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
             # Fonts still blocked — a mid-sequence font swap would look
             # like a second kind of motion and muddy what this is meant
             # to show. `--force-prefers-reduced-motion` is deliberately
             # NOT here: that is the one flag this tool exists to omit.
             "--host-resolver-rules=MAP fonts.googleapis.com 127.0.0.1,"
             "MAP fonts.gstatic.com 127.0.0.1",
             "--disable-background-networking", "--disable-sync",
             "--disable-default-apps", "--disable-component-update",
             "--metrics-recording-only", "--no-default-browser-check",
             "--no-service-autorun",
             "--disable-features=Translate,OptimizationHints",
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            return _drive(port, page_path, out_dir)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def _drive(port: int, page_path: Path, out_dir: Path) -> list[Path]:
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/version", timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise TimeoutError("devtools endpoint never came up")

    target_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{page_path.resolve().as_uri()}",
        method="PUT")
    with urllib.request.urlopen(target_req, timeout=5) as r:
        target = json.loads(r.read())
    ws_url = target["webSocketDebuggerUrl"]
    host_port, _, path = ws_url[len("ws://"):].partition("/")
    host, ws_port = host_port.split(":")

    frames: list[Path] = []
    with socket.create_connection((host, int(ws_port)), timeout=20.0) as ws:
        ws.settimeout(20.0)
        _ws_handshake(ws, host, int(ws_port), "/" + path)
        msg_id = 0

        def call(method: str, params: dict | None = None) -> dict:
            nonlocal msg_id
            msg_id += 1
            _ws_send(ws, {"id": msg_id, "method": method, "params": params or {}})
            while True:
                response = _ws_recv(ws)
                if response.get("id") == msg_id:
                    return response

        call("Page.enable")
        call("Emulation.setDeviceMetricsOverride", {
            "width": WIDTH, "height": HEIGHT, "deviceScaleFactor": 1,
            "mobile": False})
        ready_deadline = time.monotonic() + 20.0
        while time.monotonic() < ready_deadline:
            state = call("Runtime.evaluate", {
                "expression": "document.readyState", "returnByValue": True})
            if (state.get("result", {}).get("result", {}).get("value")
                    == "complete"):
                break
            time.sleep(0.05)

        import base64
        for i in range(FRAME_COUNT):
            shot = call("Page.captureScreenshot", {"format": "png"})
            data = shot.get("result", {}).get("data")
            if data:
                out = out_dir / f"frame-{i}.png"
                out.write_bytes(base64.b64decode(data))
                frames.append(out)
            if i < FRAME_COUNT - 1:
                time.sleep(FRAME_INTERVAL_S)
    return frames


def _filmstrip_html(slug: str, frames: list[Path]) -> str:
    tiles = "".join(
        f'<figure><img src="{f.name}"><figcaption>t = {i * FRAME_INTERVAL_S:.1f}s'
        f'</figcaption></figure>'
        for i, f in enumerate(frames))
    return f"""<!doctype html><meta charset="utf-8">
<title>Motion preview — {slug}</title>
<style>
 body{{margin:0;padding:24px;background:#111;color:#eee;
   font:13px/1.4 -apple-system,sans-serif}}
 h1{{font-size:15px}}
 p{{color:#999;max-width:60ch}}
 .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:20px}}
 figure{{margin:0}} img{{width:100%;border:1px solid #333;border-radius:6px}}
 figcaption{{margin-top:6px;color:#888}}
</style>
<h1>{slug} — real motion, {len(frames)} frames over
  {(len(frames) - 1) * FRAME_INTERVAL_S:.0f}s</h1>
<p>Human review only. Every other screenshot in this project forces
  prefers-reduced-motion so verdicts and collision checks stay
  reproducible — this is the one place motion is deliberately left on to
  see the choreography exist. Not read by any test.</p>
<div class="grid">{tiles}</div>
"""


def main() -> int:
    binary = chrome()
    if not binary:
        print("No Chrome or Chromium found.", file=sys.stderr)
        return 1
    slugs = sys.argv[1:] or None
    OUT.mkdir(parents=True, exist_ok=True)

    with db.session(FIXTURE_DB) as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            if slugs and path.stem not in slugs:
                continue
            slug = path.stem
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            spec = spec_from_config(dict(stored.get("config") or {}))
            page = build_from_spec(brief, spec)
            site_file = OUT / f"{slug}.html"
            site_file.write_text(_link_photographs(page, brief))

            # The plain substring "hero-stills" is in every page's inlined
            # stylesheet regardless of use (styles.py always emits the
            # rule) — only the actual wrapping div means this fixture's
            # hero really rendered the backdrop.
            if '<div class="hero-stills">' not in page:
                print(f"  {slug:18} no motion on this fixture — skipped")
                continue

            frame_dir = FILMSTRIP_DIR / slug
            frames = capture_filmstrip(binary, site_file, frame_dir)
            (frame_dir / "index.html").write_text(_filmstrip_html(slug, frames))
            print(f"  {slug:18} {len(frames)} frames -> {frame_dir / 'index.html'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
