"""Create Phase 9 loss protection policy and decision ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0010"
down_revision: str | None = "20260825_0009"
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
        "loss_protection_policies",
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("configuration_version", name="uq_loss_protection_policy_version"),
    )
    op.create_table(
        "loss_protection_decisions",
        sa.Column("dynamic_risk_decision_id", sa.Uuid(), nullable=False),
        sa.Column("loss_protection_policy_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("protection_multiplier", sa.Numeric(18, 12), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("binding_controls", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["dynamic_risk_decision_id"], ["dynamic_risk_decisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["loss_protection_policy_id"], ["loss_protection_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dynamic_risk_decision_id", name="uq_loss_decision_dynamic"),
    )


def downgrade() -> None:
    op.drop_table("loss_protection_decisions")
    op.drop_table("loss_protection_policies")
