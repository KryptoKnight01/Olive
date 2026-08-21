"""Create the Phase 1 domain and asset master schema.

Revision ID: 20260821_0002
Revises: 20260821_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_0002"
down_revision: str | None = "20260821_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

asset_class = sa.Enum(
    "CRYPTO",
    "EQUITY",
    "ETF",
    "INDEX",
    "COMMODITY",
    "FUTURES",
    "FX",
    "CASH",
    name="asset_class",
    native_enum=False,
    create_constraint=True,
)
record_status = ("ACTIVE", "SUSPENDED", "RETIRED")


def status_enum(name: str) -> sa.Enum:
    return sa.Enum(
        *record_status,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def identity_columns() -> list[sa.Column]:
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
        "assets",
        *identity_columns(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("asset_class", asset_class, nullable=False),
        sa.Column("currency_code", sa.String(3)),
        sa.Column(
            "status",
            status_enum("asset_status"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_assets_code"),
    )
    op.create_table(
        "venues",
        *identity_columns(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("country_code", sa.String(2)),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column(
            "status",
            status_enum("venue_status"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_venues_code"),
    )
    op.create_table(
        "portfolios",
        *identity_columns(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            status_enum("portfolio_status"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_portfolios_code"),
    )
    op.create_table(
        "strategies",
        *identity_columns(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column(
            "status",
            status_enum("strategy_status"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_strategies_code"),
    )
    op.create_table(
        "underlyings",
        *identity_columns(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("primary_asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "asset_class",
            sa.Enum(
                "CRYPTO",
                "EQUITY",
                "ETF",
                "INDEX",
                "COMMODITY",
                "FUTURES",
                "FX",
                "CASH",
                name="underlying_asset_class",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("country_code", sa.String(2)),
        sa.Column("sector", sa.String(80)),
        sa.Column("industry", sa.String(120)),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            status_enum("underlying_status"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["primary_asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_underlyings_code"),
    )
    op.create_index("ix_underlyings_primary_asset_id", "underlyings", ["primary_asset_id"])
    op.create_table(
        "accounts",
        *identity_columns(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column(
            "environment",
            sa.Enum(
                "DEVELOPMENT",
                "TESTING",
                "PAPER",
                "STAGING",
                "PRODUCTION",
                name="account_environment",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("external_reference", sa.String(160), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            status_enum("account_status"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint(
            "venue_id", "environment", "external_reference", name="uq_accounts_external"
        ),
    )
    op.create_index("ix_accounts_portfolio_id", "accounts", ["portfolio_id"])
    op.create_index("ix_accounts_venue_id", "accounts", ["venue_id"])
    op.create_table(
        "instruments",
        *identity_columns(),
        sa.Column("code", sa.String(96), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("base_asset_id", sa.Uuid(), nullable=False),
        sa.Column("quote_asset_id", sa.Uuid(), nullable=False),
        sa.Column("settlement_asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "instrument_type",
            sa.Enum(
                "SPOT",
                "EQUITY",
                "ETF",
                "INDEX",
                "FUTURE",
                "PERPETUAL",
                "CFD",
                "FX_SPOT",
                name="instrument_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("tick_size", sa.Numeric(30, 12), nullable=False),
        sa.Column("lot_size", sa.Numeric(30, 12), nullable=False),
        sa.Column("contract_multiplier", sa.Numeric(30, 12), nullable=False),
        sa.Column("max_leverage", sa.Numeric(12, 4)),
        sa.Column("shortable", sa.Boolean(), nullable=False),
        sa.Column("session_name", sa.String(80)),
        sa.Column(
            "status",
            status_enum("instrument_status"),
            nullable=False,
        ),
        sa.CheckConstraint("contract_multiplier > 0", name="ck_instruments_multiplier_positive"),
        sa.CheckConstraint("lot_size > 0", name="ck_instruments_lot_size_positive"),
        sa.CheckConstraint(
            "max_leverage IS NULL OR max_leverage >= 1", name="ck_instruments_leverage"
        ),
        sa.CheckConstraint("tick_size > 0", name="ck_instruments_tick_size_positive"),
        sa.ForeignKeyConstraint(["base_asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quote_asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["settlement_asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["underlying_id"], ["underlyings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_instruments_code"),
    )
    for column in ("base_asset_id", "quote_asset_id", "settlement_asset_id", "underlying_id"):
        op.create_index(f"ix_instruments_{column}", "instruments", [column])
    op.create_table(
        "strategy_versions",
        *identity_columns(),
        sa.Column("strategy_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("configuration_version", sa.String(64), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "DEVELOPMENT",
                "BACKTEST",
                "PAPER",
                "STAGING",
                "LIVE",
                "SUSPENDED",
                "RETIRED",
                name="strategy_version_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("strategy_id", "code_hash", name="uq_strategy_versions_hash"),
        sa.UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_version"),
    )
    op.create_index("ix_strategy_versions_strategy_id", "strategy_versions", ["strategy_id"])
    op.create_table(
        "venue_instruments",
        *identity_columns(),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(96), nullable=False),
        sa.Column(
            "status",
            status_enum("venue_instrument_status"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("venue_id", "instrument_id", name="uq_venue_instruments_mapping"),
        sa.UniqueConstraint("venue_id", "symbol", name="uq_venue_instruments_symbol"),
    )
    op.create_index("ix_venue_instruments_instrument_id", "venue_instruments", ["instrument_id"])
    op.create_index(
        "ix_venue_instruments_lookup", "venue_instruments", ["venue_id", "symbol", "status"]
    )


def downgrade() -> None:
    op.drop_table("venue_instruments")
    op.drop_table("strategy_versions")
    op.drop_table("instruments")
    op.drop_table("accounts")
    op.drop_table("underlyings")
    op.drop_table("strategies")
    op.drop_table("portfolios")
    op.drop_table("venues")
    op.drop_table("assets")
