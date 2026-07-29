"""The ``businesses`` table — one row per business, carrying the lifecycle state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enums import BusinessStatus
from app.core.types import GUID, enum_values


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Discovery/qualification fields (Phase 2).
    place_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(400), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # What the source *claimed* as a website (unverified; may be social/None).
    existing_site_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Whether a real, reachable site was verified by probing (never copied from
    # the source's claim — see app/stages/qualify.py).
    has_site: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    opportunity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[BusinessStatus] = mapped_column(
        SAEnum(
            BusinessStatus,
            name="business_status",
            native_enum=False,
            length=32,
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=BusinessStatus.DISCOVERED,
        index=True,
        nullable=False,
    )
    geo_country: Mapped[str] = mapped_column(String(2), default="US", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"<Business {self.name!r} status={self.status.value}>"
