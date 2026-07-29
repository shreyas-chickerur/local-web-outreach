"""Portable column types so the same models run on SQLite (dev/test) and
PostgreSQL (production)."""

from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """``values_callable`` for SQLAlchemy ``Enum`` columns.

    SQLAlchemy persists an enum member's *name* by default; this forces it to
    persist the *value* instead, so the stored representation is the lowercase
    ``.value`` (e.g. ``site``/``approve``) consistently across tables and matches
    the CHECK constraint declared in the migration.
    """
    return [member.value for member in enum_cls]


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's native ``UUID`` when available, otherwise stores a
    36-character stringified UUID (SQLite). Values are always surfaced to
    Python as ``uuid.UUID``.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
