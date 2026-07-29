"""The ``site_weaknesses`` table — concrete, evidenced defects found on a
business's existing website (or its absence). Feeds the opportunity score and,
later, the "why the old site is weak" panel in the approval console."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enums import Severity
from app.core.types import GUID, enum_values


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SiteWeakness(Base):
    __tablename__ = "site_weaknesses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("businesses.id"), index=True, nullable=False
    )
    # Stable machine key, e.g. "no_site", "no_https", "not_mobile_responsive".
    issue: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[Severity] = mapped_column(
        SAEnum(
            Severity,
            name="weakness_severity",
            native_enum=False,
            length=8,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"<SiteWeakness {self.issue} sev={self.severity.value}>"
