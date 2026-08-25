"""Create Phase 34 advanced execution plans."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0035"
down_revision = "20260825_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "advanced_execution_plans",
        sa.Column("order_id", sa.String(120), nullable=False, unique=True),
        sa.Column("style", sa.String(32), nullable=False),
        sa.Column("total_quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("slices", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("advanced_execution_plans")
