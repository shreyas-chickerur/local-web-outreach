"""Shared fixtures.

Default backend is a throwaway SQLite file (zero external dependencies). A
Postgres fixture spins up a fresh temporary database per test and skips cleanly
when no server is reachable.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text

from app.core.db import Base, make_engine, make_session_factory
from app.models import Approval, AuditEvent, Business  # noqa: F401  (register metadata)

PG_ADMIN_URL = os.environ.get("TEST_PG_ADMIN_URL", "postgresql+psycopg2:///postgres")


# --------------------------------------------------------------------------- #
# SQLite (default)
# --------------------------------------------------------------------------- #
@pytest.fixture
def engine(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    eng = make_engine(url)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return make_session_factory(engine)


@pytest.fixture
def session(session_factory):
    s = session_factory()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


# --------------------------------------------------------------------------- #
# PostgreSQL (skipped when unavailable)
# --------------------------------------------------------------------------- #
@pytest.fixture
def pg_url():
    """Create and drop a fresh temp Postgres database; skip if no server."""
    try:
        admin = make_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
        dbname = f"lwo_test_{uuid.uuid4().hex[:12]}"
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    except Exception as exc:  # pragma: no cover - env dependent
        pytest.skip(f"PostgreSQL not available: {exc}")

    url = f"postgresql+psycopg2:///{dbname}"
    try:
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ),
                {"db": dbname},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}"'))
        admin.dispose()


@pytest.fixture
def pg_engine(pg_url):
    eng = make_engine(pg_url)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def pg_session(pg_engine):
    s = make_session_factory(pg_engine)()
    try:
        yield s
    finally:
        s.rollback()
        s.close()
