"""The ``websites`` table — a generated site draft for a business.

The site is a **private proposal** (``DRAFT``, tokenized preview, noindex) until
the operator approves it (Gate 1) and, later, the client buys and it goes
``LIVE``. ``content_json`` is the structured, fact-traceable content model;
``content_hash`` binds an approval to the exact reviewed content.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enums import WebsiteState
from app.core.types import GUID, enum_values


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("businesses.id"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    preview_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    preview_url: Mapped[str] = mapped_column(String(300), nullable=False)
    state: Mapped[WebsiteState] = mapped_column(
        SAEnum(
            WebsiteState,
            name="website_state",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=WebsiteState.DRAFT,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"<Website business={self.business_id} v{self.version} state={self.state.value}>"
