"""The ``emails`` table — outreach (and later, reply) emails.

An email stays ``DRAFT`` until Gate 2 (operator approval); ``content_hash`` binds
an approval to the exact reviewed text. ``suppression_checked`` records that the
recipient was cleared against the suppression list at compose time.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base
from app.core.enums import EmailKind, EmailStatus
from app.core.types import GUID, enum_values


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("businesses.id"), index=True, nullable=False
    )
    kind: Mapped[EmailKind] = mapped_column(
        SAEnum(EmailKind, name="email_kind", native_enum=False, length=16,
               create_constraint=True, values_callable=enum_values),
        nullable=False,
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    footer: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EmailStatus] = mapped_column(
        SAEnum(EmailStatus, name="email_status", native_enum=False, length=16,
               create_constraint=True, values_callable=enum_values),
        default=EmailStatus.DRAFT, nullable=False,
    )
    suppression_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inbox_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"<Email {self.kind.value} to={self.recipient} status={self.status.value}>"
