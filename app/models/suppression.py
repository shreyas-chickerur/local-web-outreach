"""The ``suppression_list`` table — recipients that must never be contacted.

Populated by unsubscribes/complaints/bounces (Phase 8) or manual entry. Checked
at compose time (Phase 6) by exact email or by domain.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base
from app.core.enums import SuppressionReason
from app.core.types import GUID, enum_values


class SuppressionEntry(Base):
    __tablename__ = "suppression_list"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Exact email OR a bare domain (e.g. "example.com"); one of them is set.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reason: Mapped[SuppressionReason] = mapped_column(
        SAEnum(SuppressionReason, name="suppression_reason", native_enum=False, length=16,
               create_constraint=True, values_callable=enum_values),
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        target = self.email or f"@{self.domain}"
        return f"<SuppressionEntry {target} ({self.reason.value})>"
