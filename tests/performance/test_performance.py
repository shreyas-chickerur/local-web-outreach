"""Performance guardrails for the spine.

Thresholds are deliberately generous (they assert the spine is not accidentally
O(n) per write or pathologically slow); the measured numbers are printed so
regressions are visible in CI logs. Run with ``-s`` to see them locally.
"""

from __future__ import annotations

import time
import uuid

import pytest

from app.core.audit import record_event, verify_chain
from app.core.enums import BusinessStatus as S
from app.core.state_machine import advance
from app.models.business import Business

pytestmark = pytest.mark.performance

N_EVENTS = 2000
N_BUSINESSES = 500


def test_audit_write_throughput(session, capsys):
    start = time.perf_counter()
    for i in range(N_EVENTS):
        record_event(
            session,
            actor="worker",
            action=f"perf:{i}",
            subject_type="business",
            subject_id=uuid.uuid4(),
            after={"i": i},
        )
    session.commit()
    elapsed = time.perf_counter() - start
    rate = N_EVENTS / elapsed

    with capsys.disabled():
        print(f"\n[perf] audit write: {N_EVENTS} events in {elapsed:.3f}s -> {rate:,.0f}/s")

    # Guardrail: appends must not collapse below a very conservative floor.
    assert rate > 100, f"audit write throughput too low: {rate:.0f}/s"


def test_verify_chain_scale(session, capsys):
    for i in range(N_EVENTS):
        record_event(session, actor="worker", action=f"perf:{i}", subject_type="business")
    session.commit()

    start = time.perf_counter()
    ok, bad = verify_chain(session)
    elapsed = time.perf_counter() - start

    with capsys.disabled():
        print(f"[perf] verify chain: {N_EVENTS} events in {elapsed:.3f}s")

    assert ok is True and bad is None
    assert elapsed < 10.0, f"chain verification too slow: {elapsed:.2f}s for {N_EVENTS}"


def test_state_machine_throughput(session, capsys):
    businesses = []
    for _ in range(N_BUSINESSES):
        biz = Business(name="Acme", location="Galena, IL")
        session.add(biz)
        businesses.append(biz)
    session.flush()

    start = time.perf_counter()
    for biz in businesses:
        advance(session, biz, S.QUALIFIED)
    session.commit()
    elapsed = time.perf_counter() - start
    rate = N_BUSINESSES / elapsed

    with capsys.disabled():
        print(f"[perf] advance: {N_BUSINESSES} transitions in {elapsed:.3f}s -> {rate:,.0f}/s")

    assert rate > 50, f"state-machine throughput too low: {rate:.0f}/s"
