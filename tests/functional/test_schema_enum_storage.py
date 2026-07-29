"""Regression: the *migration-built* schema must accept and store exactly what
the ORM writes, using the enum ``.value`` (lowercase), enforced by a CHECK.

This closes the gap that let a name-vs-value mismatch hide: the other functional
tests build the schema with ``create_all`` (model-defined), so they could never
catch a divergence between the ORM's persisted representation and the migration's
declared domain. Here we build the schema via Alembic and insert through the ORM.
"""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.approvals import create_approval
from app.core.db import make_engine, make_session_factory
from app.core.enums import Decision, SubjectType
from app.models.business import Business

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _migrate(url: str):
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    return make_engine(url)


@pytest.mark.functional
def test_orm_writes_enum_values_into_migrated_schema(tmp_path):
    engine = _migrate(f"sqlite+pysqlite:///{tmp_path / 'mig.db'}")
    session = make_session_factory(engine)()
    try:
        biz = Business(name="Acme", location="Galena, IL")
        session.add(biz)
        session.flush()
        create_approval(
            session,
            subject_type=SubjectType.SITE,
            subject_id=biz.id,
            decision=Decision.APPROVE,
            approver="shreyas",
        )
        session.commit()

        status = session.execute(text("SELECT status FROM businesses")).scalar_one()
        subj, dec = session.execute(
            text("SELECT subject_type, decision FROM approvals")
        ).one()

        # Stored as lowercase .value, consistently — not the uppercase member name.
        assert status == "DISCOVERED"
        assert subj == "site"
        assert dec == "approve"
    finally:
        session.rollback()
        session.close()
        engine.dispose()


@pytest.mark.functional
def test_check_constraint_rejects_unknown_enum_value(tmp_path):
    engine = _migrate(f"sqlite+pysqlite:///{tmp_path / 'mig.db'}")
    session = make_session_factory(engine)()
    try:
        # A raw insert with a value outside the declared domain must be rejected
        # by the CHECK constraint the migration installs.
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO approvals (id, subject_type, subject_id, decision, "
                    "approver, decided_at) VALUES (:id, 'bogus', :sid, 'approve', "
                    "'x', '2026-07-29T00:00:00+00:00')"
                ),
                {"id": str(uuid.uuid4()), "sid": str(uuid.uuid4())},
            )
            session.commit()
    finally:
        session.rollback()
        session.close()
        engine.dispose()
