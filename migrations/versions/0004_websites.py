"""websites: generated site drafts

Revision ID: 0004_websites
Revises: 0003_research
Create Date: 2026-07-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision: str = "0004_websites"
down_revision: Union[str, None] = "0003_research"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "websites",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("business_id", GUID(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("preview_token", sa.String(length=64), nullable=False),
        sa.Column("preview_url", sa.String(length=300), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "draft", "approved", "live", "rejected",
                name="website_state", native_enum=False, length=16,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("preview_token", name="uq_websites_preview_token"),
    )
    op.create_index("ix_websites_business_id", "websites", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_websites_business_id", table_name="websites")
    op.drop_table("websites")
