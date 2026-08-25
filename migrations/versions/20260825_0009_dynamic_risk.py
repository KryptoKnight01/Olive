"""Create Phase 8 dynamic risk policy and decision ledger.

Revision ID: 20260825_0009
Revises: 20260824_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0009"
down_revision: str | None = "20260824_0008"
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
        "dynamic_risk_policies",
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("bounds", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("configuration_version", name="uq_dynamic_risk_policy_version"),
    )
    op.create_table(
        "dynamic_risk_decisions",
        sa.Column("correlation_risk_decision_id", sa.Uuid(), nullable=False),
        sa.Column("dynamic_risk_policy_id", sa.Uuid(), nullable=False),
        sa.Column("base_risk_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("raw_multipliers", sa.JSON(), nullable=False),
        sa.Column("bounded_multipliers", sa.JSON(), nullable=False),
        sa.Column("multiplier_product", sa.Numeric(20, 12), nullable=False),
        sa.Column("uncapped_risk_pct", sa.Numeric(20, 12), nullable=False),
        sa.Column("final_risk_pct", sa.Numeric(20, 12), nullable=False),
        sa.Column("caps", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["correlation_risk_decision_id"],
            ["correlation_risk_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dynamic_risk_policy_id"], ["dynamic_risk_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "correlation_risk_decision_id", name="uq_dynamic_decision_correlation"
        ),
    )


def downgrade() -> None:
    op.drop_table("dynamic_risk_decisions")
    op.drop_table("dynamic_risk_policies")
