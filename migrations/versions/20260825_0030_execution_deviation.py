"""Create Phase 29 live/paper deviation reports."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0030"
down_revision = "20260825_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_deviation_reports",
        sa.Column("signal_id", sa.String(120), nullable=False),
        sa.Column("delay_delta_ms", sa.Integer(), nullable=False),
        sa.Column("slippage_pct", sa.Numeric(12, 6)),
        sa.Column("pnl_divergence", sa.Numeric(24, 8), nullable=False),
        sa.Column("breached", sa.Boolean(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_execution_deviation_reports_signal_id", "execution_deviation_reports", ["signal_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_execution_deviation_reports_signal_id", table_name="execution_deviation_reports"
    )
    op.drop_table("execution_deviation_reports")
