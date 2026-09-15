"""Phase 2 ("prove the seam"), Step 3's corpus verification.

    .venv/bin/python tools/seam_corpus_check.py

Re-runs the ported gates (`app.site.seam_gates.gate`) against the real
19-fixture corpus's own rendered output, and against both planted-
fabrication seam pages with their <script> actually executed -- all
through ONE real browser session, this round's own resource rule
(Browser launches: one process for the whole round, reused, single
worker). Not a standing test: a real headless-Chrome render per fixture
is exactly the cost this round's rules say not to pay on every
`make check`, so this is a tool to run deliberately, like
`tools/contact_sheet.py` or `tools/content_census.py`, not a CI gate.

Prints, per fixture: how many findings the OLD gate (source-markup,
regex-over-five-classes) reported versus the PORTED gate
(`visible_text_runs` over the rendered DOM), and any finding the port
raises that the old gate did not -- each one is either a real
fabrication the old gate missed, or a false positive that means a rule
in `seam_gates.py` needs widening, never a fixture to change. See
`.reviews/phase-2-seam.md` for the false positives this found and fixed
before the corpus came back clean.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

from app.adapters.chrome_cdp import cdp_session, chrome
from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.provenance import unexplained_sentences
from app.site.render import build_from_spec, material_from_brief, unsupported
from app.site.seam_gates import gate as ported_gate
from app.site.visible import render, visible_text_runs
from app.store import db, leads, sites

FIXTURES = Path("tests/fixtures/briefs")
SEAM = Path("tests/fixtures/seam")
OUT = Path("tools/seam_corpus_check_results.json")


def main() -> int:
    binary = chrome()
    if not binary:
        print("No Chrome or Chromium found.", file=sys.stderr)
        return 1

    t0 = time.time()
    results: list[dict] = []

    with cdp_session(binary, "about:blank", 1440, 900, 1.0, timeout=30.0) as call:

        # 0. prove render() itself works, in this same session.
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe.html"
            probe.write_text(
                "<html><body><div id='slot'></div>"
                "<script>document.getElementById('slot').textContent"
                " = 'added by script';</script></body></html>")
            dom = render(call, probe.resolve().as_uri(), timeout=30.0)
        assert "added by script" in dom, "render() did not return script-added content"
        print("render() verified: script-added content present in returned DOM")

        # 1. class 5, for real, on both seam foreign pages.
        for name in ("hvac-foreign", "restaurant-casual-foreign"):
            manifest = json.loads((SEAM / f"{name}.manifest.json").read_text())
            page = SEAM / f"{name}.html"
            dom = render(call, page.resolve().as_uri(), timeout=30.0)
            runs = visible_text_runs(dom)
            brief = json.loads(Path(manifest["brief"]).read_text())
            material = material_from_brief(brief)
            findings = ported_gate(runs, material)
            planting = next(p for p in manifest["plantings"] if p.get("script_injected"))
            caught = any(planting["sentence"].lower() in f.lower()
                        or f.lower() in planting["sentence"].lower() for f in findings)
            print(f"{name}: class 5 caught for REAL (actual script execution) = {caught}")
            if not caught:
                print(f"  !! findings were: {findings}")

        # 2. the 19-fixture corpus, old gate vs ported gate.
        with db.session(":memory:") as conn:
            for path in sorted(FIXTURES.glob("*.json")):
                slug = path.stem
                lead_id = leads.save_brief(conn, json.loads(path.read_text()))
                for stage in STAGES:
                    run_stage(conn, lead_id, stage)
                brief = leads.brief_with_overrides(conn, lead_id)
                stored = sites.recall_stage(conn, lead_id, "direction") or {}
                config = dict(stored.get("config") or {})
                if config.get("read_by") != "frozen":
                    print(f"{slug}: SKIPPED -- did not replay a frozen direction")
                    continue
                spec = spec_from_config(config)
                page_html = build_from_spec(brief, spec)
                material = material_from_brief(brief)

                old_findings = (unsupported(page_html, material)
                               + unexplained_sentences(page_html, material))

                with tempfile.TemporaryDirectory() as tmp:
                    page_path = Path(tmp) / f"{slug}.html"
                    page_path.write_text(page_html)
                    dom = render(call, page_path.resolve().as_uri(), timeout=30.0)
                runs = visible_text_runs(dom)
                new_findings = ported_gate(runs, material)

                new_only = [f for f in new_findings if f not in old_findings]
                results.append({
                    "slug": slug, "old_count": len(old_findings),
                    "new_count": len(new_findings), "new_only": new_only,
                })
                flag = "  <-- NEW FINDING(S)" if new_only else ""
                print(f"{slug:20} old={len(old_findings):2}  new={len(new_findings):2}{flag}")
                for f in new_only:
                    print(f"    + {f!r}")

    print()
    print(f"total time: {time.time() - t0:.0f}s")
    OUT.write_text(json.dumps(results, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
