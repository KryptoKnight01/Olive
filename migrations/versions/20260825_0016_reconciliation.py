"""Create Phase 15 reconciliation ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0016"
down_revision = "20260825_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_runs",
        sa.Column("matched", sa.Boolean(), nullable=False),
        sa.Column("suspend_entries", sa.Boolean(), nullable=False),
        sa.Column("mismatches", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("reconciliation_runs")
