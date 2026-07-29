"""Capability-B eval: generated site content is grounded and correct.

For the bundled Frisco businesses, checks that:
  1. the industry template matches the category,
  2. EVERY rendered fact traces to a VERIFIED claim,
  3. no forbidden (fabricated social-proof) sections appear, and
  4. UNVERIFIED fields are never rendered as facts.

Bar: 100% (grounding/no-fabrication invariants). Run: `python -m evals.site_eval`.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.ai.research_runner import PassthroughExtractor
from app.core.db import Base, make_engine, make_session_factory
from app.core.enums import BusinessStatus, ClaimStatus
from app.demo_data import demo_businesses
from app.models.business import Business
from app.models.research_claim import ResearchClaim
from app.stages.generate import FORBIDDEN_SECTIONS, generate_website
from app.stages.research import build_dossier

EXPECTED_TEMPLATE = {"restaurant": "restaurant", "lawn": "service"}


def run() -> tuple[bool, list[str]]:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    extractor = PassthroughExtractor()
    report: list[str] = []
    passed = total = 0

    def check(cond: bool, label: str) -> None:
        nonlocal passed, total
        total += 1
        passed += bool(cond)
        report.append(f"[{'PASS' if cond else 'FAIL'}] {label}")

    try:
        for entry in demo_businesses():
            sources = entry.pop("sources")
            biz = Business(status=BusinessStatus.RESEARCHED, **entry)
            session.add(biz)
            session.flush()
            build_dossier(session, biz, sources, extractor, model_version="eval")
            site = generate_website(session, biz)
            content = site.content_json
            name = biz.name

            claims = session.execute(
                select(ResearchClaim).where(ResearchClaim.business_id == biz.id)
            ).scalars().all()
            verified_ids = {str(c.id) for c in claims if c.status is ClaimStatus.VERIFIED}
            unverified_fields = {c.field for c in claims if c.status is not ClaimStatus.VERIFIED}
            facts = [f for s in content["sections"] for f in s.get("facts", [])]
            rendered_fields = {f["field"] for f in facts}

            check(content["industry"] == EXPECTED_TEMPLATE.get(biz.category, "generic"),
                  f"{name}: template correct ({content['industry']})")
            check(all(f["claim_id"] in verified_ids for f in facts),
                  f"{name}: all {len(facts)} facts trace to a VERIFIED claim")
            check(all(s["type"] not in FORBIDDEN_SECTIONS for s in content["sections"]),
                  f"{name}: no fabricated social-proof sections")
            check(not (unverified_fields & rendered_fields),
                  f"{name}: unverified fields not rendered as facts")
        session.rollback()
    finally:
        session.close()
        engine.dispose()

    ok = total > 0 and passed == total
    report.append(f"\nCapability B: {passed}/{total} checks passed "
                  f"-> {'PASS' if ok else 'FAIL'} (bar: 100%)")
    return ok, report


if __name__ == "__main__":  # pragma: no cover
    ok, lines = run()
    print("\n".join(lines))
    sys.exit(0 if ok else 1)
