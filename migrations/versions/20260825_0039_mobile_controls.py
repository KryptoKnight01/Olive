"""Create Phase 38 mobile control decisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0039"
down_revision = "20260825_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mobile_control_decisions",
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("permitted", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(120), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_mobile_control_decisions_user_id", "mobile_control_decisions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_mobile_control_decisions_user_id", table_name="mobile_control_decisions")
    op.drop_table("mobile_control_decisions")
