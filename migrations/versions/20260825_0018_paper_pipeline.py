"""Create Phase 17 paper pipeline run ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0018"
down_revision = "20260825_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_pipeline_runs",
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_status", sa.String(24), nullable=False),
        sa.Column("protection_status", sa.String(24), nullable=False),
        sa.Column("reconciled", sa.Boolean(), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(30, 12), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("paper_pipeline_runs")
