"""Create Phase 3 signal validation policies and outcomes.

Revision ID: 20260824_0004
Revises: 20260821_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0004"
down_revision: str | None = "20260821_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("signal_intake_status", "signal_intake_records", type_="check")
    op.alter_column(
        "signal_intake_records",
        "status",
        existing_type=sa.String(8),
        type_=sa.String(11),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "signal_intake_status",
        "signal_intake_records",
        "status IN ('RECEIVED', 'REJECTED', 'RISK_REVIEW')",
    )
    op.add_column("signal_intake_records", sa.Column("validation_details", sa.JSON()))
    op.add_column("signal_intake_records", sa.Column("validated_at", sa.DateTime(timezone=True)))
    op.create_table(
        "signal_validation_policies",
        sa.Column("strategy_version_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("allowed_directions", sa.JSON(), nullable=False),
        sa.Column("allowed_timeframes", sa.JSON(), nullable=False),
        sa.Column("max_entry_deviation_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("min_expected_rr", sa.Numeric(10, 4), nullable=False),
        sa.Column("min_setup_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("session_timezone", sa.String(64), nullable=False),
        sa.Column("session_start", sa.String(5)),
        sa.Column("session_end", sa.String(5)),
        sa.Column("allowed_weekdays", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_entry_deviation_pct >= 0", name="ck_validation_entry_deviation_nonnegative"
        ),
        sa.CheckConstraint("min_expected_rr >= 0", name="ck_validation_min_rr_nonnegative"),
        sa.CheckConstraint(
            "min_setup_score >= 0 AND min_setup_score <= 100",
            name="ck_validation_setup_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"], ["strategy_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("strategy_version_id", name="uq_signal_validation_policy_version"),
    )


def downgrade() -> None:
    op.drop_table("signal_validation_policies")
    op.drop_column("signal_intake_records", "validated_at")
    op.drop_column("signal_intake_records", "validation_details")
    op.drop_constraint("signal_intake_status", "signal_intake_records", type_="check")
    op.create_check_constraint(
        "signal_intake_status",
        "signal_intake_records",
        "status IN ('RECEIVED', 'REJECTED')",
    )
    op.alter_column(
        "signal_intake_records",
        "status",
        existing_type=sa.String(11),
        type_=sa.String(8),
        existing_nullable=False,
    )
