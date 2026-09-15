"""Phase 2b's own corpus verification.

    .venv/bin/python tools/seam_corpus_check.py

Re-runs the fixed gate (`app.site.seam_gates.gate`) against the real
19-fixture corpus's own SOURCE HTML (`build_from_spec()`'s own output,
read directly -- Phase 2b's resource rule is no browser at all, and
render.py's own <script> tag is purely behavioural, confirmed in Phase
2: scroll effects, lightbox, menu filtering, no visible text added).

Prints, per fixture: how many findings the OLD gate (source markup,
regex-over-five-classes) reported versus the FIXED gate, and any
finding the fixed gate raises that the old gate did not -- each one is
either a real uncorroborated claim or number our own renderer shipped
(report it, do not fix the fixture) or a gate false positive (fix the
rule, and confirm the planted corpus still catches everything). See
`.reviews/phase-2b-seam.md` for the false positives this found and
fixed before the corpus came back clean, and why that zero is earned,
not tuned: every fix traces to a real, documented gap in the RULE
(a deterministic heading never recognised, a phone number's digit
groups never corroborated, a review's platform attribution), never to
loosening what counts as a claim or an unbacked number -- the planted
corpus (tests/sitegen/test_seam_gates.py) still catches every class,
checked after each fix, not just at the end.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.site.pipeline import STAGES, run_stage, spec_from_config
from app.site.provenance import unexplained_sentences
from app.site.render import build_from_spec, material_from_brief, unsupported
from app.site.seam_gates import gate as ported_gate
from app.site.visible import visible_text_runs
from app.store import db, leads, sites

FIXTURES = Path("tests/fixtures/briefs")
OUT = Path("tools/seam_corpus_check_results.json")


def main() -> int:
    results: list[dict] = []
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
            runs = visible_text_runs(page_html)
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

    OUT.write_text(json.dumps(results, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
