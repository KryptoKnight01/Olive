"""Create Phase 16 sandbox operation ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0017"
down_revision = "20260825_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sandbox_operations",
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("external_reference", sa.String(100)),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("sandbox_operations")
