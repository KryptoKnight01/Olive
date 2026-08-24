"""Create Phase 6 hierarchical exposure limits and decision ledger.

Revision ID: 20260824_0007
Revises: 20260824_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0007"
down_revision: str | None = "20260824_0006"
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
        "hierarchical_exposure_limits",
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("scope_key", sa.String(200), nullable=False),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("maximum", sa.Numeric(30, 8), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("maximum > 0", name="ck_hierarchical_limit_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "configuration_version",
            "dimension",
            "scope_key",
            "metric",
            name="uq_hierarchical_limit_identity",
        ),
    )
    op.create_table(
        "hierarchical_risk_decisions",
        sa.Column("portfolio_risk_decision_id", sa.Uuid(), nullable=False),
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("approved_fraction", sa.Numeric(18, 12), nullable=False),
        sa.Column("approved_notional", sa.Numeric(30, 8), nullable=False),
        sa.Column("binding_limit", sa.String(500), nullable=True),
        sa.Column("evaluations", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["portfolio_risk_decision_id"],
            ["portfolio_risk_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portfolio_risk_decision_id", name="uq_hierarchy_decision_portfolio"
        ),
    )


def downgrade() -> None:
    op.drop_table("hierarchical_risk_decisions")
    op.drop_table("hierarchical_exposure_limits")
