"""initial spine: businesses, audit_events, approvals (+ pg append-only triggers)

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PG_APPEND_ONLY = """
CREATE OR REPLACE FUNCTION lwo_prevent_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'append-only: % on % is not permitted', TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_events_append_only
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION lwo_prevent_mutation();

CREATE TRIGGER approvals_append_only
    BEFORE UPDATE OR DELETE ON approvals
    FOR EACH ROW EXECUTE FUNCTION lwo_prevent_mutation();
"""

_PG_APPEND_ONLY_DOWN = """
DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
DROP TRIGGER IF EXISTS approvals_append_only ON approvals;
DROP FUNCTION IF EXISTS lwo_prevent_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DISCOVERED", "QUALIFIED", "RESEARCHED", "SITE_DRAFTED", "SITE_APPROVED",
                "EMAIL_DRAFTED", "EMAIL_APPROVED", "SENT", "REPLIED", "NEGOTIATING",
                "WON", "LOST", "SUPPRESSED", "DISQUALIFIED",
                name="business_status", native_enum=False, length=32,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("geo_country", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_businesses_status", "businesses", ["status"])

    op.create_table(
        "audit_events",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("ts", sa.String(length=40), nullable=False),
        sa.Column("actor", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", GUID(), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("approval_id", GUID(), nullable=True),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("seq", name="uq_audit_events_seq"),
        sa.UniqueConstraint("hash", name="uq_audit_events_hash"),
    )
    op.create_index("ix_audit_events_seq", "audit_events", ["seq"])

    op.create_table(
        "approvals",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "subject_type",
            sa.Enum(
                "site", "email", "reply",
                name="approval_subject_type", native_enum=False, length=16,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("subject_id", GUID(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "approve", "reject", "edit", "request_changes",
                name="approval_decision", native_enum=False, length=16,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("approver", sa.String(length=120), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approvals_subject_id", "approvals", ["subject_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(_PG_APPEND_ONLY)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(_PG_APPEND_ONLY_DOWN)

    op.drop_index("ix_approvals_subject_id", table_name="approvals")
    op.drop_table("approvals")
    op.drop_index("ix_audit_events_seq", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_businesses_status", table_name="businesses")
    op.drop_table("businesses")
