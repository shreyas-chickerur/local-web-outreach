"""research: research_claims table

Revision ID: 0003_research
Revises: 0002_discovery
Create Date: 2026-07-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision: str = "0003_research"
down_revision: Union[str, None] = "0002_discovery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_claims",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("business_id", GUID(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "verified", "unverified", "conflict",
                name="claim_status", native_enum=False, length=16,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("corroborations", sa.Integer(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_claims_business_id", "research_claims", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_research_claims_business_id", table_name="research_claims")
    op.drop_table("research_claims")
