"""Store Google's published rating so a second platform can corroborate it.

Revision ID: 0006_ratings
Revises: 0005_email
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_ratings"
down_revision = "0005_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("businesses")}
    if "rating" not in cols:
        op.add_column("businesses", sa.Column("rating", sa.Float(), nullable=True))
    if "review_count" not in cols:
        op.add_column("businesses", sa.Column("review_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("businesses", "review_count")
    op.drop_column("businesses", "rating")
