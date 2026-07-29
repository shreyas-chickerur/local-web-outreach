"""Postgres defense-in-depth: DB-level triggers must reject UPDATE/DELETE on the
append-only tables even for raw SQL that bypasses the application guard."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import InternalError, ProgrammingError

from app.core.audit import record_event
from app.core.db import make_engine, make_session_factory

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

pytestmark = [pytest.mark.functional, pytest.mark.postgres]


def _migrated_engine(url: str):
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    return make_engine(url)


def test_db_trigger_blocks_raw_update(pg_url):
    engine = _migrated_engine(pg_url)
    session = make_session_factory(engine)()
    try:
        record_event(session, actor="worker", action="x", subject_type="business")
        session.commit()
        with pytest.raises((InternalError, ProgrammingError)):
            session.execute(text("UPDATE audit_events SET action = 'tampered'"))
            session.commit()
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def test_db_trigger_blocks_raw_delete(pg_url):
    engine = _migrated_engine(pg_url)
    session = make_session_factory(engine)()
    try:
        record_event(session, actor="worker", action="x", subject_type="business")
        session.commit()
        with pytest.raises((InternalError, ProgrammingError)):
            session.execute(text("DELETE FROM audit_events"))
            session.commit()
    finally:
        session.rollback()
        session.close()
        engine.dispose()
