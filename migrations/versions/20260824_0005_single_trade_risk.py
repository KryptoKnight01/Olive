"""Create Phase 4 single-trade risk policy and decision ledger.

Revision ID: 20260824_0005
Revises: 20260824_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0005"
down_revision: str | None = "20260824_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "single_trade_risk_policies",
        sa.Column("strategy_version_id", sa.Uuid(), nullable=False),
        sa.Column("base_risk_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("max_risk_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("max_notional", sa.Numeric(30, 8), nullable=False),
        sa.Column("max_leverage", sa.Numeric(12, 4), nullable=False),
        sa.Column("max_margin", sa.Numeric(30, 8), nullable=False),
        sa.Column("min_stop_distance_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("max_stop_distance_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("base_risk_pct > 0", name="ck_trade_risk_base_positive"),
        sa.CheckConstraint("max_risk_pct > 0", name="ck_trade_risk_max_positive"),
        sa.CheckConstraint("max_notional > 0", name="ck_trade_risk_notional_positive"),
        sa.CheckConstraint("max_leverage >= 1", name="ck_trade_risk_leverage"),
        sa.CheckConstraint("max_margin > 0", name="ck_trade_risk_margin_positive"),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"], ["strategy_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("strategy_version_id", name="uq_trade_risk_policy_version"),
    )
    op.create_table(
        "trade_risk_decisions",
        sa.Column("signal_intake_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("requested_risk_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("approved_risk_pct", sa.Numeric(10, 8), nullable=False),
        sa.Column("position_size", sa.Numeric(30, 12), nullable=False),
        sa.Column("base_risk_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("equity_snapshot", sa.Numeric(30, 8), nullable=False),
        sa.Column("available_margin_snapshot", sa.Numeric(30, 8), nullable=False),
        sa.Column("multipliers", sa.JSON(), nullable=False),
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
            ["signal_intake_id"], ["signal_intake_records.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_intake_id", name="uq_trade_risk_decision_signal"),
    )


def downgrade() -> None:
    op.drop_table("trade_risk_decisions")
    op.drop_table("single_trade_risk_policies")
