"""Create Phase 12 execution risk policy and decision ledgers.

Revision ID: 20260825_0013
Revises: 20260825_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0013"
down_revision: str | None = "20260825_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "execution_risk_policies",
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("configuration_version", name="uq_execution_risk_policy_version"),
    )
    op.create_table(
        "execution_risk_decisions",
        sa.Column("market_quote_id", sa.Uuid(), nullable=False),
        sa.Column("execution_risk_policy_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("requested_quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("approved_quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("requested_notional", sa.Numeric(30, 12), nullable=False),
        sa.Column("approved_notional", sa.Numeric(30, 12), nullable=False),
        sa.Column("maximum_executable_notional", sa.Numeric(30, 12), nullable=False),
        sa.Column("slice_count", sa.Integer(), nullable=False),
        sa.Column("binding_limits", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["market_quote_id"], ["market_quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["execution_risk_policy_id"], ["execution_risk_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("execution_risk_decisions")
    op.drop_table("execution_risk_policies")
