"""Create Phase 10 portfolio regime policy and decision ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0011"
down_revision: str | None = "20260825_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        "portfolio_regime_policies",
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("controls", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("configuration_version", name="uq_regime_policy_version"),
    )
    op.create_table(
        "portfolio_regime_decisions",
        sa.Column("loss_protection_decision_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_regime_policy_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("regime", sa.String(32), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("metric_regimes", sa.JSON(), nullable=False),
        sa.Column("controls", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["loss_protection_decision_id"], ["loss_protection_decisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_regime_policy_id"], ["portfolio_regime_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loss_protection_decision_id", name="uq_regime_decision_protection"),
    )


def downgrade() -> None:
    op.drop_table("portfolio_regime_decisions")
    op.drop_table("portfolio_regime_policies")
