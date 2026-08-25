"""Create Phase 28 limited-live decision ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0029"
down_revision = "20260825_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "live_capital_decisions",
        sa.Column("signal_id", sa.String(120), nullable=False, unique=True),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("approved_notional", sa.Numeric(24, 8), nullable=False),
        sa.Column("route_permitted", sa.Boolean(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("live_capital_decisions")
