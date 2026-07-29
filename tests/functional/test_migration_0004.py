"""Migration 0004 must apply/reverse and accept ORM writes on the built schema."""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.db import make_engine, make_session_factory
from app.core.enums import BusinessStatus, WebsiteState
from app.models.business import Business
from app.models.website import Website

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _cfg(url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.mark.functional
def test_migration_0004_up_down_sqlite(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm4.db'}"
    cfg = _cfg(url)
    engine = make_engine(url)
    try:
        command.upgrade(cfg, "head")
        assert "websites" in inspect(engine).get_table_names()
        command.downgrade(cfg, "base")
        assert "websites" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


@pytest.mark.functional
def test_migrated_schema_accepts_websites(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm4.db'}"
    command.upgrade(_cfg(url), "head")
    engine = make_engine(url)
    session = make_session_factory(engine)()
    try:
        biz = Business(name="Acme", location="Frisco, TX", place_id="p1",
                       status=BusinessStatus.SITE_DRAFTED)
        session.add(biz)
        session.flush()
        session.add(Website(
            business_id=biz.id, version=1, content_json={"sections": []},
            preview_token="tok123", preview_url="https://preview-tok123.lwo.example/",
            state=WebsiteState.DRAFT, content_hash="abc",
        ))
        session.commit()

        state = session.execute(text("SELECT state FROM websites")).scalar_one()
        assert state == "draft"

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO websites (id, business_id, version, content_json, "
                    "preview_token, preview_url, state, content_hash, created_at) VALUES "
                    "(:id, :bid, 1, '{}', 'tok2', 'u', 'bogus', 'h', "
                    "'2026-07-29T00:00:00+00:00')"
                ),
                {"id": str(uuid.uuid4()), "bid": str(biz.id)},
            )
            session.commit()
    finally:
        session.rollback()
        session.close()
        engine.dispose()
