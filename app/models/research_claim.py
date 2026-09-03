"""The ``research_claims`` table — atomic, sourced, confidence-scored facts.

Each row is one field/value pair for a business, carrying the sources that
support it, a corroboration count, a confidence score, and a status. Only
``VERIFIED`` claims may be rendered as fact on a generated site (invariant #1).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base
from app.core.enums import ClaimStatus
from app.core.types import GUID, enum_values


class ResearchClaim(Base):
    __tablename__ = "research_claims"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("businesses.id"), index=True, nullable=False
    )
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    # Null when status is CONFLICT (no single agreed value).
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(
        SAEnum(
            ClaimStatus,
            name="claim_status",
            native_enum=False,
            length=24,   # fits "operator_verified"
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    corroborations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # List of {"source_type": ..., "source_url": ...} dicts.
    sources: Mapped[list] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Set when a human vouches for this claim. Attribution is the whole point:
    # an operator-verified fact must always name its operator.
    verified_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    @property
    def ships_as_fact(self) -> bool:
        """Machine-corroborated OR vouched for by a named human."""
        return self.status in (ClaimStatus.VERIFIED, ClaimStatus.OPERATOR_VERIFIED)

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"<ResearchClaim {self.field}={self.value!r} status={self.status.value}>"
