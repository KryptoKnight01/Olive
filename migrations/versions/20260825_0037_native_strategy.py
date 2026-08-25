"""Create Phase 36 native strategy signals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0037"
down_revision = "20260825_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_strategy_signals",
        sa.Column("strategy_key", sa.String(120), nullable=False),
        sa.Column("direction", sa.Integer(), nullable=False),
        sa.Column("specification_version", sa.String(80), nullable=False),
        sa.Column("reason", sa.String(160), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_native_strategy_signals_strategy_key", "native_strategy_signals", ["strategy_key"]
    )


def downgrade() -> None:
    op.drop_index("ix_native_strategy_signals_strategy_key", table_name="native_strategy_signals")
    op.drop_table("native_strategy_signals")
