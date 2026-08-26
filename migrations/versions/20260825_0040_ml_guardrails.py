"""Create Phase 39 ML guardrail decisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0040"
down_revision = "20260825_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ml_guardrail_decisions",
        sa.Column("model_key", sa.String(120), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("applied_multiplier", sa.Numeric(12, 6), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_ml_guardrail_decisions_model_key", "ml_guardrail_decisions", ["model_key"])


def downgrade() -> None:
    op.drop_index("ix_ml_guardrail_decisions_model_key", table_name="ml_guardrail_decisions")
    op.drop_table("ml_guardrail_decisions")
