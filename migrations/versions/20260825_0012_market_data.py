"""Create normalized market quote and OHLCV storage.

Revision ID: 20260825_0012
Revises: 20260825_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0012"
down_revision: str | None = "20260825_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_quotes",
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("venue_code", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bid", sa.Numeric(30, 12), nullable=False),
        sa.Column("ask", sa.Numeric(30, 12), nullable=False),
        sa.Column("last", sa.Numeric(30, 12)),
        sa.Column("volume", sa.Numeric(30, 12)),
        sa.Column("mid", sa.Numeric(30, 12), nullable=False),
        sa.Column("spread", sa.Numeric(30, 12), nullable=False),
        sa.Column("spread_pct", sa.Numeric(18, 12), nullable=False),
        sa.Column("age_seconds", sa.Numeric(18, 6), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_quotes_instrument_source_time",
        "market_quotes",
        ["instrument_id", "source_timestamp"],
    )
    op.create_table(
        "market_ohlcv",
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("venue_code", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(30, 12), nullable=False),
        sa.Column("high", sa.Numeric(30, 12), nullable=False),
        sa.Column("low", sa.Numeric(30, 12), nullable=False),
        sa.Column("close", sa.Numeric(30, 12), nullable=False),
        sa.Column("volume", sa.Numeric(30, 12), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "instrument_id", "venue_code", "source", "timeframe", "open_time",
            name="uq_market_ohlcv_bar",
        ),
    )


def downgrade() -> None:
    op.drop_table("market_ohlcv")
    op.drop_index("ix_market_quotes_instrument_source_time", table_name="market_quotes")
    op.drop_table("market_quotes")
