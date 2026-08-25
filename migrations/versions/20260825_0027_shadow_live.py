"""Create Phase 26 shadow-live runs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0027"
down_revision = "20260825_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shadow_live_runs",
        sa.Column("signal_id", sa.String(120), nullable=False, unique=True),
        sa.Column("hypothetical_notional", sa.Numeric(24, 8), nullable=False),
        sa.Column("sent_to_venue", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("shadow_live_runs")
