"""Create Phase 30 venue-route decisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0031"
down_revision = "20260825_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "venue_route_decisions",
        sa.Column("venue", sa.String(120)),
        sa.Column("approved_notional", sa.Numeric(24, 8), nullable=False),
        sa.Column("effective_price", sa.Numeric(24, 8)),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("venue_route_decisions")
