"""Create Phase 27 live-readiness reviews."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0028"
down_revision = "20260825_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "live_readiness_reviews",
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("failed_checks", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("live_readiness_reviews")
