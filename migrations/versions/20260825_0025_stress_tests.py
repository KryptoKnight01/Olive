"""Create Phase 24 stress-test results."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0025"
down_revision = "20260825_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stress_test_results",
        sa.Column("scenario", sa.String(120), nullable=False),
        sa.Column("projected_loss", sa.Numeric(24, 8), nullable=False),
        sa.Column("projected_loss_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("contributors", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("stress_test_results")
