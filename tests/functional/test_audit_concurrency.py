"""Concurrency stress for the audit ledger (PostgreSQL).

Many threads append events at once. The per-chain advisory lock in
``record_event`` must keep the chain linear: exactly N rows, seqs 1..N with no
gaps or duplicates, and ``verify_chain`` passing. Without the lock, concurrent
writers would race the tip read and produce duplicate seqs (unique-violation) or
a broken hash chain. Skips when no PostgreSQL server is reachable.
"""

from __future__ import annotations

import threading
import uuid

import pytest
from sqlalchemy import func, select

from app.core.audit import record_event, verify_chain
from app.core.db import make_session_factory
from app.models.audit import AuditEvent

pytestmark = [pytest.mark.functional, pytest.mark.postgres]

THREADS = 8
PER_THREAD = 25


def test_concurrent_writers_keep_chain_linear(pg_engine):
    session_factory = make_session_factory(pg_engine)
    errors: list[Exception] = []

    def worker() -> None:
        for _ in range(PER_THREAD):
            s = session_factory()
            try:
                record_event(
                    s, actor="worker", action="advance:X->Y", subject_type="business",
                    subject_id=uuid.uuid4(), after={"reason": "concurrent"},
                )
                s.commit()
            except Exception as exc:  # noqa: BLE001 - collected and asserted below
                errors.append(exc)
                s.rollback()
            finally:
                s.close()

    threads = [threading.Thread(target=worker) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"writers errored (likely a seq race): {errors[:3]}"

    check = session_factory()
    try:
        total = check.execute(select(func.count()).select_from(AuditEvent)).scalar_one()
        seqs = list(check.execute(select(AuditEvent.seq).order_by(AuditEvent.seq)).scalars())
        expected = THREADS * PER_THREAD
        assert total == expected
        # contiguous, gapless, no duplicates — proof the lock serialized seq assignment
        assert seqs == list(range(1, expected + 1))
        ok, bad = verify_chain(check)
        assert ok is True, f"audit chain broke at seq {bad}"
    finally:
        check.close()
