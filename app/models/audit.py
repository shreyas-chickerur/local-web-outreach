"""The ``audit_events`` table — an append-only, hash-chained ledger.

Every state transition and every outbound-authorizing action writes one row.
Each row's ``hash`` is ``sha256(canonical_json(payload))`` where the payload
includes the previous row's ``hash`` (``prev_hash``), forming a tamper-evident
chain. ``seq`` gives a total order; it is assigned under a chain lock in
``app.core.audit`` so the chain stays linear even under concurrent writers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import GUID


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Monotonic order of the chain (assigned app-side under a lock).
    seq: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    # Canonical UTC ISO-8601 timestamp string used verbatim in the hash payload.
    ts: Mapped[str] = mapped_column(String(40), nullable=False)
    actor: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    # Reserved for future free-text; kept nullable so hashing ignores it.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"<AuditEvent seq={self.seq} action={self.action!r}>"
