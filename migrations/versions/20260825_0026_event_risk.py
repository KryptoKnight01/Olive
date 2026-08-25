"""Create Phase 25 event-risk decisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0026"
down_revision = "20260825_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_risk_decisions",
        sa.Column("event_key", sa.String(120), nullable=False),
        sa.Column("entries_allowed", sa.Boolean(), nullable=False),
        sa.Column("risk_multiplier", sa.Numeric(12, 6), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_event_risk_decisions_event_key", "event_risk_decisions", ["event_key"])


def downgrade() -> None:
    op.drop_index("ix_event_risk_decisions_event_key", table_name="event_risk_decisions")
    op.drop_table("event_risk_decisions")
