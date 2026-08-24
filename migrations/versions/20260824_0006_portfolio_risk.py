"""Create Phase 5 portfolio risk policy and decision ledger.

Revision ID: 20260824_0006
Revises: 20260824_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0006"
down_revision: str | None = "20260824_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_risk_policies",
        sa.Column("scope_key", sa.String(100), nullable=False),
        sa.Column("max_gross_exposure_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("max_net_exposure_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("max_long_exposure_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("max_short_exposure_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("max_open_stop_risk_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("max_margin_utilization_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("max_leverage", sa.Numeric(12, 4), nullable=False),
        sa.Column("max_concurrent_positions", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("max_concurrent_positions > 0", name="ck_portfolio_positions_positive"),
        sa.CheckConstraint("max_leverage >= 1", name="ck_portfolio_risk_leverage"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_key", name="uq_portfolio_risk_policy_scope"),
    )
    op.create_table(
        "portfolio_risk_decisions",
        sa.Column("trade_risk_decision_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_risk_policy_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("approved_fraction", sa.Numeric(18, 12), nullable=False),
        sa.Column("approved_notional", sa.Numeric(30, 8), nullable=False),
        sa.Column("current_snapshot", sa.JSON(), nullable=False),
        sa.Column("projected_snapshot", sa.JSON(), nullable=False),
        sa.Column("limits", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_risk_policy_id"],
            ["portfolio_risk_policies.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trade_risk_decision_id"], ["trade_risk_decisions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_risk_decision_id", name="uq_portfolio_decision_trade_risk"),
    )


def downgrade() -> None:
    op.drop_table("portfolio_risk_decisions")
    op.drop_table("portfolio_risk_policies")
