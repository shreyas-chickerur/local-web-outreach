"""Engine/session factory plus the application-layer append-only guard.

The append-only guard is registered once on the SQLAlchemy ``Session`` class and
matches by table name, so it needs no import of the ORM models (avoids an import
cycle). It is the *portable* enforcement of invariant #3 and runs on every
backend. PostgreSQL additionally installs DB-level triggers (see the Alembic
migration) as defense-in-depth.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.errors import AppendOnlyError

# Tables that may only ever be inserted into — never updated or deleted.
APPEND_ONLY_TABLES = frozenset({"audit_events", "approvals"})


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def make_engine(url: str, *, echo: bool = False, **kwargs) -> Engine:
    """Create an engine, enabling SQLite foreign-key enforcement when relevant."""
    engine = create_engine(url, echo=echo, future=True, **kwargs)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_conn, _record):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a configured session factory bound to ``engine``."""
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@event.listens_for(Session, "before_flush")
def _append_only_guard(session: Session, _flush_context, _instances) -> None:  # noqa: ANN001
    """Reject any UPDATE or DELETE targeting an append-only table."""
    for obj in session.dirty:
        if getattr(obj, "__tablename__", None) in APPEND_ONLY_TABLES and session.is_modified(
            obj, include_collections=False
        ):
            raise AppendOnlyError(
                f"UPDATE on append-only table '{obj.__tablename__}' is not permitted"
            )
    for obj in session.deleted:
        if getattr(obj, "__tablename__", None) in APPEND_ONLY_TABLES:
            raise AppendOnlyError(
                f"DELETE on append-only table '{obj.__tablename__}' is not permitted"
            )
