"""Create Phase 22 kill-switch state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0023"
down_revision = "20260825_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kill_switches",
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("scope_key", sa.String(120), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("scope", "scope_key", name="uq_kill_switch_scope"),
    )


def downgrade() -> None:
    op.drop_table("kill_switches")
