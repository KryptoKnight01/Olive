"""Create Phase 33 capital pool ledgers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0034"
down_revision = "20260825_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capital_pool_ledgers",
        sa.Column("pool_key", sa.String(120), nullable=False),
        sa.Column("allocated_capital", sa.Numeric(24, 8), nullable=False),
        sa.Column("investor_units", sa.Numeric(24, 8), nullable=False),
        sa.Column("metadata_values", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_capital_pool_ledgers_pool_key", "capital_pool_ledgers", ["pool_key"])


def downgrade() -> None:
    op.drop_index("ix_capital_pool_ledgers_pool_key", table_name="capital_pool_ledgers")
    op.drop_table("capital_pool_ledgers")
