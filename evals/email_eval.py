"""Capability-C eval: outreach emails are compliant, grounded, and non-deceptive.

For each bundled Frisco business, run research → generate → approve site → compose
the outreach email, then check the CAN-SPAM + grounding properties:
  1. footer carries the physical postal address,
  2. footer carries an opt-out,
  3. body contains the preview link (exactly one CTA),
  4. body references the business by name (a true specific), and
  5. the subject is non-deceptive.

Bar: 100%. (The "would a human send this?" quality bar is inherently manual;
the suppression guard is covered by unit tests.) Run: `python -m evals.email_eval`.
"""

from __future__ import annotations

import sys

from app.ai.email_composer import TemplateEmailComposer
from app.ai.research_runner import PassthroughExtractor
from app.core import config
from app.core.approvals import create_approval
from app.core.compliance import validate_subject
from app.core.db import Base, make_engine, make_session_factory
from app.core.enums import Actor, BusinessStatus, Decision, SubjectType
from app.core.errors import ComplianceError
from app.core.state_machine import advance
from app.demo_data import demo_businesses
from app.models.business import Business
from app.stages.generate import generate_website
from app.stages.outreach import compose_email
from app.stages.research import build_dossier


def _subject_ok(subject: str) -> bool:
    try:
        validate_subject(subject)
        return True
    except ComplianceError:
        return False


def run() -> tuple[bool, list[str]]:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    extractor = PassthroughExtractor()
    postal = config.sender_postal_address()
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
            approval = create_approval(session, subject_type=SubjectType.SITE,
                                       subject_id=biz.id, decision=Decision.APPROVE,
                                       approver="eval", content=site.content_json)
            advance(session, biz, BusinessStatus.SITE_APPROVED,
                    actor=Actor.HUMAN.value, approval=approval)
            email = compose_email(session, biz, TemplateEmailComposer())
            name = biz.name

            check(postal in email.footer, f"{name}: footer has postal address")
            check("unsubscribe" in email.footer.lower(), f"{name}: footer has opt-out")
            check(email.body.count(site.preview_url) == 1, f"{name}: exactly one CTA (preview)")
            check(name in email.body, f"{name}: body references the business by name")
            check(_subject_ok(email.subject), f"{name}: subject is non-deceptive")
        session.rollback()
    finally:
        session.close()
        engine.dispose()

    ok = total > 0 and passed == total
    report.append(f"\nCapability C: {passed}/{total} checks passed "
                  f"-> {'PASS' if ok else 'FAIL'} (bar: 100%)")
    return ok, report


if __name__ == "__main__":  # pragma: no cover
    ok, lines = run()
    print("\n".join(lines))
    sys.exit(0 if ok else 1)
