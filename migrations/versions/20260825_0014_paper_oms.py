"""Create Phase 13 paper OMS ledgers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260825_0014"
down_revision = "20260825_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def common() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "paper_orders",
        sa.Column("client_order_id", sa.Uuid(), unique=True, nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column(
            "instrument_id",
            sa.Uuid(),
            sa.ForeignKey("instruments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("average_fill_price", sa.Numeric(30, 12)),
        sa.Column("fees", sa.Numeric(30, 12), nullable=False),
        sa.Column("reduce_only", sa.Boolean(), nullable=False),
        *common(),
    )
    op.create_table(
        "paper_fills",
        sa.Column(
            "order_id",
            sa.Uuid(),
            sa.ForeignKey("paper_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("price", sa.Numeric(30, 12), nullable=False),
        sa.Column("fee", sa.Numeric(30, 12), nullable=False),
        *common(),
    )
    op.create_table(
        "paper_positions",
        sa.Column(
            "instrument_id",
            sa.Uuid(),
            sa.ForeignKey("instruments.id", ondelete="RESTRICT"),
            unique=True,
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("average_entry_price", sa.Numeric(30, 12), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(30, 12), nullable=False),
        sa.Column("fees", sa.Numeric(30, 12), nullable=False),
        *common(),
    )


def downgrade() -> None:
    op.drop_table("paper_positions")
    op.drop_table("paper_fills")
    op.drop_table("paper_orders")
