"""Create Phase 32 asset-eligibility decisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0033"
down_revision = "20260825_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_eligibility_decisions",
        sa.Column("asset_class", sa.String(80), nullable=False),
        sa.Column("instrument", sa.String(120), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("approved_notional", sa.Numeric(24, 8), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_asset_eligibility_decisions_asset_class", "asset_eligibility_decisions", ["asset_class"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_asset_eligibility_decisions_asset_class", table_name="asset_eligibility_decisions"
    )
    op.drop_table("asset_eligibility_decisions")
