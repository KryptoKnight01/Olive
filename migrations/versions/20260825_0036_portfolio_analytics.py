"""Create Phase 35 portfolio analytics."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0036"
down_revision = "20260825_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_analytics",
        sa.Column("portfolio_key", sa.String(120), nullable=False),
        sa.Column("value_at_risk", sa.Numeric(24, 8), nullable=False),
        sa.Column("expected_shortfall", sa.Numeric(24, 8), nullable=False),
        sa.Column("analytics", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_portfolio_analytics_portfolio_key", "portfolio_analytics", ["portfolio_key"]
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_analytics_portfolio_key", table_name="portfolio_analytics")
    op.drop_table("portfolio_analytics")
