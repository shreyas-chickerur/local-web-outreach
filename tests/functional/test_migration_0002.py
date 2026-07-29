"""Migration 0002 must apply/reverse and the migration-built schema must accept
what the ORM writes (including the new columns and the severity CHECK)."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.db import make_engine, make_session_factory
from app.core.enums import BusinessStatus, Severity
from app.models.business import Business
from app.models.site_weakness import SiteWeakness

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NEW_COLUMNS = {"place_id", "address", "phone", "existing_site_url", "has_site",
               "opportunity_score"}


def _cfg(url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.mark.functional
def test_migration_0002_up_down_sqlite(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm2.db'}"
    cfg = _cfg(url)
    engine = make_engine(url)
    try:
        command.upgrade(cfg, "head")
        insp = inspect(engine)
        assert "site_weaknesses" in insp.get_table_names()
        cols = {c["name"] for c in insp.get_columns("businesses")}
        assert NEW_COLUMNS <= cols

        command.downgrade(cfg, "base")
        tables = set(inspect(engine).get_table_names())
        assert "site_weaknesses" not in tables
        assert "businesses" not in tables
    finally:
        engine.dispose()


@pytest.mark.functional
def test_migrated_schema_accepts_orm_writes(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm2.db'}"
    command.upgrade(_cfg(url), "head")
    engine = make_engine(url)
    session = make_session_factory(engine)()
    try:
        biz = Business(
            name="JS Lawn Care Service", location="Frisco, TX", place_id="jslawn",
            existing_site_url=None, has_site=False, opportunity_score=3,
            status=BusinessStatus.QUALIFIED,
        )
        session.add(biz)
        session.flush()
        session.add(SiteWeakness(business_id=biz.id, issue="no_site", severity=Severity.HIGH,
                                 evidence="no real website"))
        session.commit()

        sev = session.execute(text("SELECT severity FROM site_weaknesses")).scalar_one()
        assert sev == "high"  # stored as .value, enforced by CHECK

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO site_weaknesses (id, business_id, issue, severity, detected_at) "
                    "VALUES ('x', :bid, 'no_site', 'catastrophic', '2026-07-29T00:00:00+00:00')"
                ),
                {"bid": str(biz.id)},
            )
            session.commit()
    finally:
        session.rollback()
        session.close()
        engine.dispose()


@pytest.mark.functional
@pytest.mark.postgres
def test_migration_0002_up_down_postgres(pg_url):
    cfg = _cfg(pg_url)
    engine = make_engine(pg_url)
    try:
        command.upgrade(cfg, "head")
        assert "site_weaknesses" in inspect(engine).get_table_names()
        command.downgrade(cfg, "base")
        assert "site_weaknesses" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
