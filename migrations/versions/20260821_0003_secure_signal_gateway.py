"""Create the Phase 2 secure signal intake ledger.

Revision ID: 20260821_0003
Revises: 20260821_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_0003"
down_revision: str | None = "20260821_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def constrained_enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def upgrade() -> None:
    op.create_table(
        "signal_intake_records",
        sa.Column("signal_id", sa.Uuid()),
        sa.Column(
            "status",
            constrained_enum("RECEIVED", "REJECTED", name="signal_intake_status"),
            nullable=False,
        ),
        sa.Column("rejection_code", sa.String(64)),
        sa.Column("rejection_reason", sa.String(500)),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("raw_payload", sa.JSON()),
        sa.Column("strategy_version_id", sa.Uuid()),
        sa.Column("venue_instrument_id", sa.Uuid()),
        sa.Column("configuration_version", sa.String(64)),
        sa.Column(
            "environment",
            constrained_enum(
                "development",
                "testing",
                "paper",
                "staging",
                "production",
                name="signal_environment",
            ),
        ),
        sa.Column("emitted_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "direction",
            constrained_enum("LONG", "SHORT", name="signal_direction"),
        ),
        sa.Column("entry_price", sa.Numeric(30, 12)),
        sa.Column("reference_price", sa.Numeric(30, 12)),
        sa.Column("stop_price", sa.Numeric(30, 12)),
        sa.Column("targets", sa.JSON()),
        sa.Column("expected_rr", sa.Numeric(18, 8)),
        sa.Column("timeframe", sa.String(32)),
        sa.Column("setup_score", sa.Numeric(8, 4)),
        sa.Column("regime", sa.String(64)),
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
        sa.CheckConstraint("expected_rr IS NULL OR expected_rr >= 0", name="ck_signal_expected_rr"),
        sa.CheckConstraint(
            "setup_score IS NULL OR (setup_score >= 0 AND setup_score <= 100)",
            name="ck_signal_setup_score",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"], ["strategy_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["venue_instrument_id"], ["venue_instruments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id"),
    )
    op.create_index(
        "ix_signal_intake_records_strategy_version_id",
        "signal_intake_records",
        ["strategy_version_id"],
    )
    op.create_index(
        "ix_signal_intake_records_venue_instrument_id",
        "signal_intake_records",
        ["venue_instrument_id"],
    )
    op.create_index("ix_signal_intake_payload_hash", "signal_intake_records", ["payload_hash"])
    op.create_index(
        "ix_signal_intake_status_created",
        "signal_intake_records",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("signal_intake_records")
