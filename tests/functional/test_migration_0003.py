"""Migration 0003 must apply/reverse and accept ORM writes on the built schema."""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.db import make_engine, make_session_factory
from app.core.enums import BusinessStatus, ClaimStatus
from app.models.business import Business
from app.models.research_claim import ResearchClaim

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _cfg(url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.mark.functional
def test_migration_0003_up_down_sqlite(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm3.db'}"
    cfg = _cfg(url)
    engine = make_engine(url)
    try:
        command.upgrade(cfg, "head")
        assert "research_claims" in inspect(engine).get_table_names()
        command.downgrade(cfg, "base")
        assert "research_claims" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


@pytest.mark.functional
def test_migrated_schema_accepts_research_claims(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm3.db'}"
    command.upgrade(_cfg(url), "head")
    engine = make_engine(url)
    session = make_session_factory(engine)()
    try:
        biz = Business(name="Acme", location="Frisco, TX", place_id="p1",
                       status=BusinessStatus.RESEARCHED)
        session.add(biz)
        session.flush()
        session.add(ResearchClaim(
            business_id=biz.id, field="address", value="6733 W Main St",
            status=ClaimStatus.VERIFIED, confidence=0.9, corroborations=2,
            sources=[{"source_type": "yelp", "source_url": "https://x"}],
            model_version="test",
        ))
        session.commit()

        status = session.execute(text("SELECT status FROM research_claims")).scalar_one()
        assert status == "verified"  # stored as .value, CHECK-enforced

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO research_claims (id, business_id, field, status, confidence, "
                    "corroborations, sources, extracted_at) VALUES (:id, :bid, 'x', 'bogus', "
                    "0.5, 1, '[]', '2026-07-29T00:00:00+00:00')"
                ),
                {"id": str(uuid.uuid4()), "bid": str(biz.id)},
            )
            session.commit()
    finally:
        session.rollback()
        session.close()
        engine.dispose()
