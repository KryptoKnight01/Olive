"""Create Phase 7 correlation risk policy and decision ledger.

Revision ID: 20260824_0008
Revises: 20260824_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0008"
down_revision: str | None = "20260824_0007"
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
        "correlation_risk_policies",
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("lookback_observations", sa.Integer(), nullable=False),
        sa.Column("minimum_observations", sa.Integer(), nullable=False),
        sa.Column("cluster_threshold", sa.Numeric(10, 8), nullable=False),
        sa.Column("max_correlated_positions", sa.Integer(), nullable=False),
        sa.Column("max_cluster_stop_risk", sa.Numeric(30, 8), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("minimum_observations >= 3", name="ck_correlation_minimum_history"),
        sa.CheckConstraint(
            "lookback_observations >= minimum_observations", name="ck_correlation_lookback"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("configuration_version", name="uq_correlation_policy_version"),
    )
    op.create_table(
        "correlation_risk_decisions",
        sa.Column("hierarchical_risk_decision_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_risk_policy_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("approved_fraction", sa.Numeric(18, 12), nullable=False),
        sa.Column("approved_notional", sa.Numeric(30, 8), nullable=False),
        sa.Column("proposed_cluster", sa.JSON(), nullable=False),
        sa.Column("correlations", sa.JSON(), nullable=False),
        sa.Column("cluster_position_count", sa.Integer(), nullable=False),
        sa.Column("current_cluster_stop_risk", sa.Numeric(30, 8), nullable=False),
        sa.Column("projected_cluster_stop_risk", sa.Numeric(30, 8), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["correlation_risk_policy_id"], ["correlation_risk_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["hierarchical_risk_decision_id"],
            ["hierarchical_risk_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "hierarchical_risk_decision_id", name="uq_correlation_decision_hierarchy"
        ),
    )


def downgrade() -> None:
    op.drop_table("correlation_risk_decisions")
    op.drop_table("correlation_risk_policies")
