"""Alembic migration must apply and fully reverse on both backends."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.db import make_engine

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPINE_TABLES = {"businesses", "audit_events", "approvals"}


def _alembic_config(url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _assert_up_then_down(url: str) -> None:
    cfg = _alembic_config(url)
    engine = make_engine(url)
    try:
        command.upgrade(cfg, "head")
        tables = set(inspect(engine).get_table_names())
        assert SPINE_TABLES.issubset(tables), f"missing tables after upgrade: {tables}"

        command.downgrade(cfg, "base")
        tables = set(inspect(engine).get_table_names())
        assert not (SPINE_TABLES & tables), f"tables remained after downgrade: {tables}"
    finally:
        engine.dispose()


@pytest.mark.functional
def test_migration_up_down_sqlite(tmp_path):
    _assert_up_then_down(f"sqlite+pysqlite:///{tmp_path / 'mig.db'}")


@pytest.mark.functional
@pytest.mark.postgres
def test_migration_up_down_postgres(pg_url):
    _assert_up_then_down(pg_url)
