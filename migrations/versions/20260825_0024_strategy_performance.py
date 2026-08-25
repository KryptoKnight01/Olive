"""Create Phase 23 strategy performance assessments."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0024"
down_revision = "20260825_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_performance_assessments",
        sa.Column("strategy_key", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("breaches", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_strategy_performance_assessments_strategy_key",
        "strategy_performance_assessments",
        ["strategy_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_performance_assessments_strategy_key",
        table_name="strategy_performance_assessments",
    )
    op.drop_table("strategy_performance_assessments")
