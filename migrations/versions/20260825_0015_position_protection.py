"""Create Phase 14 protection assessment ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0015"
down_revision = "20260825_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "protection_assessments",
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("stop_quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("target_quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("critical", sa.Boolean(), nullable=False),
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
    op.drop_table("protection_assessments")
