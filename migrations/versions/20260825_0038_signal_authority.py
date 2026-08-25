"""Create Phase 37 signal authority decisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0038"
down_revision = "20260825_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_authority_decisions",
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("production_authority_granted", sa.Boolean(), nullable=False),
        sa.Column("tradingview_required", sa.Boolean(), nullable=False),
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
    op.drop_table("signal_authority_decisions")
