"""Capability-A eval: score research dossiers against known-true Frisco facts.

Checks two safety-critical properties on the bundled data:
  1. facts we KNOW are true are surfaced as VERIFIED with the right value, and
  2. facts we DON'T know (owner, thin-data phone) are NOT fabricated as VERIFIED.

Bar: 100% of checks pass (these are correctness/no-hallucination invariants, not
soft quality metrics). Run: `python -m evals.research_eval`.
"""

from __future__ import annotations

import re
import sys

from app.ai.research_runner import PassthroughExtractor
from app.core.db import Base, make_engine, make_session_factory
from app.core.enums import BusinessStatus
from app.demo_data import GOLDEN_TRUTH, demo_businesses
from app.models.business import Business
from app.stages.research import build_dossier


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def run() -> tuple[bool, list[str]]:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    extractor = PassthroughExtractor()
    report: list[str] = []
    checks_passed = checks_total = 0

    try:
        for entry in demo_businesses():
            sources = entry.pop("sources")
            place_id = entry["place_id"]
            biz = Business(status=BusinessStatus.RESEARCHED, **entry)
            session.add(biz)
            session.flush()
            dossier = build_dossier(session, biz, sources, extractor, model_version="eval")

            verified = {c.field: c for c in dossier.verified()}
            truth = GOLDEN_TRUTH[place_id]

            for field, expected in truth["verified_must_include"].items():
                checks_total += 1
                claim = verified.get(field)
                got = (claim.value or "") if claim else ""
                ok = claim is not None and (
                    expected in got.lower() or expected in _digits(got)
                )
                checks_passed += ok
                report.append(f"[{'PASS' if ok else 'FAIL'}] {biz.name}: {field} VERIFIED "
                              f"= {expected!r} (got {got!r})")

            for field in truth["must_not_be_verified"]:
                checks_total += 1
                ok = field not in verified
                checks_passed += ok
                report.append(f"[{'PASS' if ok else 'FAIL'}] {biz.name}: {field} NOT "
                              f"fabricated as VERIFIED")
        session.rollback()
    finally:
        session.close()
        engine.dispose()

    passed = checks_total > 0 and checks_passed == checks_total
    report.append(f"\nCapability A: {checks_passed}/{checks_total} checks passed "
                  f"-> {'PASS' if passed else 'FAIL'} (bar: 100%)")
    return passed, report


if __name__ == "__main__":  # pragma: no cover
    ok, lines = run()
    print("\n".join(lines))
    sys.exit(0 if ok else 1)
