"""The ``sender_identities`` table — one row per sending mailbox.

Deliverability is a property of the *sender*, not the message. A domain that
sends too much too early, or accumulates bounces and complaints, stops being
delivered at all — and the damage is not undoable. So each mailbox carries its
own daily budget, its warmup start date, and running bounce/complaint counters,
and can be paused automatically without human intervention.

The pause is deliberately one-way in code: nothing here un-pauses a domain. That
is a judgement call for a person who has looked at why it happened.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base
from app.core.types import GUID


class SenderIdentity(Base):
    __tablename__ = "sender_identities"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # The mailbox mail is sent from, e.g. "shreyas@getbrandsites.com".
    address: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Reputation is tracked per DOMAIN, but sending happens per mailbox.
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    daily_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    warmup_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bounce_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    complaint_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paused_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    @property
    def bounce_rate(self) -> float:
        return (self.bounce_count / self.sent_count) if self.sent_count else 0.0

    @property
    def complaint_rate(self) -> float:
        return (self.complaint_count / self.sent_count) if self.sent_count else 0.0

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        state = "paused" if self.paused else "active"
        return f"<SenderIdentity {self.address} {state} sent={self.sent_count}>"
