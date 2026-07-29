"""The ``approvals`` table — immutable operator sign-offs.

An approval binds a decision to the *exact* content reviewed via ``content_hash``
so a later edit cannot silently ride on an old approval (invariant #2).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enums import Decision, SubjectType
from app.core.types import GUID, enum_values


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[SubjectType] = mapped_column(
        SAEnum(
            SubjectType,
            name="approval_subject_type",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    decision: Mapped[Decision] = mapped_column(
        SAEnum(
            Decision,
            name="approval_decision",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    approver: Mapped[str] = mapped_column(String(120), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return (
            f"<Approval {self.decision.value} {self.subject_type.value} "
            f"subject={self.subject_id}>"
        )
