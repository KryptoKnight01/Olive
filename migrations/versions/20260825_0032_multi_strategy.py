"""Create Phase 31 strategy-resolution ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0032"
down_revision = "20260825_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_resolutions",
        sa.Column("instrument", sa.String(120), nullable=False),
        sa.Column("direction", sa.Integer(), nullable=False),
        sa.Column("total_risk_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("allocations", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_strategy_resolutions_instrument", "strategy_resolutions", ["instrument"])


def downgrade() -> None:
    op.drop_index("ix_strategy_resolutions_instrument", table_name="strategy_resolutions")
    op.drop_table("strategy_resolutions")
