"""Migration 0005 must apply/reverse and accept ORM writes on the built schema."""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.db import make_engine, make_session_factory
from app.core.enums import BusinessStatus, EmailKind, EmailStatus, SuppressionReason
from app.models.business import Business
from app.models.email import Email
from app.models.suppression import SuppressionEntry

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _cfg(url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.mark.functional
def test_migration_0005_up_down_sqlite(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm5.db'}"
    cfg = _cfg(url)
    engine = make_engine(url)
    try:
        command.upgrade(cfg, "head")
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        assert {"emails", "suppression_list"} <= tables
        assert "contact_email" in {c["name"] for c in insp.get_columns("businesses")}
        command.downgrade(cfg, "base")
        assert not ({"emails", "suppression_list"} & set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()


@pytest.mark.functional
def test_migrated_schema_accepts_email_and_suppression(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'm5.db'}"
    command.upgrade(_cfg(url), "head")
    engine = make_engine(url)
    session = make_session_factory(engine)()
    try:
        biz = Business(name="Acme", location="Frisco, TX", place_id="p1",
                       contact_email="a@b.com", status=BusinessStatus.SITE_APPROVED)
        session.add(biz)
        session.flush()
        session.add(Email(business_id=biz.id, kind=EmailKind.OUTREACH, recipient="a@b.com",
                          subject="Hi", body="body", footer="foot", status=EmailStatus.DRAFT,
                          suppression_checked=True, content_hash="h"))
        session.add(SuppressionEntry(email="x@y.com", reason=SuppressionReason.UNSUBSCRIBE))
        session.commit()

        assert session.execute(text("SELECT status FROM emails")).scalar_one() == "draft"
        assert session.execute(text("SELECT reason FROM suppression_list")).scalar_one() \
            == "unsubscribe"

        # CHECK constraint rejects an out-of-domain email status
        with pytest.raises(IntegrityError):
            session.execute(
                text("INSERT INTO emails (id, business_id, kind, recipient, subject, body, "
                     "footer, status, suppression_checked, content_hash, created_at) VALUES "
                     "(:id, :bid, 'outreach', 'a@b.com', 's', 'b', 'f', 'bogus', 1, 'h', "
                     "'2026-07-29T00:00:00+00:00')"),
                {"id": str(uuid.uuid4()), "bid": str(biz.id)},
            )
            session.commit()
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def test_0007_widens_claim_status_on_a_populated_database(tmp_path):
    """Migrations run against populated legacy databases, not empty ones."""
    import sqlite3

    db = tmp_path / "legacy.db"
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE research_claims (
          id TEXT PRIMARY KEY, business_id TEXT NOT NULL, field TEXT NOT NULL,
          value TEXT, status VARCHAR(16) NOT NULL, confidence FLOAT NOT NULL,
          corroborations INTEGER NOT NULL, sources JSON NOT NULL,
          model_version VARCHAR(80), extracted_at DATETIME NOT NULL,
          CONSTRAINT claim_status CHECK (status IN ('verified','unverified','conflict'))
        );
        INSERT INTO research_claims VALUES
          ('c1','b1','phone','(972) 555-0148','verified',0.9,2,'[]',NULL,'2026-01-01');
    """)
    con.commit()
    con.close()

    cfg = _cfg(f"sqlite+pysqlite:///{db}")
    command.stamp(cfg, "0006_ratings")
    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM research_claims").fetchone()[0] == 1
    cols = {r[1] for r in con.execute("PRAGMA table_info(research_claims)")}
    assert {"verified_by", "verified_at", "verified_note"} <= cols
    # the widened CHECK admits the new value...
    cols_sql = ("id,business_id,field,value,status,confidence,corroborations,"
                "sources,extracted_at")
    con.execute(f"INSERT INTO research_claims ({cols_sql}) VALUES "
                "('c2','b1','x','y','operator_verified',1.0,0,'[]','2026-01-01')")
    # ...but still rejects nonsense
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(f"INSERT INTO research_claims ({cols_sql}) VALUES "
                    "('c3','b1','x','y','bogus',1.0,0,'[]','2026-01-01')")
    con.close()
