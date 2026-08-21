from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from olive.db import Base


def enum_column(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type, name=name, native_enum=False, create_constraint=True, validate_strings=True
    )


class AssetClass(StrEnum):
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    ETF = "ETF"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"
    FUTURES = "FUTURES"
    FX = "FX"
    CASH = "CASH"


class InstrumentType(StrEnum):
    SPOT = "SPOT"
    EQUITY = "EQUITY"
    ETF = "ETF"
    INDEX = "INDEX"
    FUTURE = "FUTURE"
    PERPETUAL = "PERPETUAL"
    CFD = "CFD"
    FX_SPOT = "FX_SPOT"


class Environment(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    PAPER = "PAPER"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class RecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class StrategyState(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    STAGING = "STAGING"
    LIVE = "LIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UuidMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class Asset(UuidMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("code", name="uq_assets_code"),)

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(
        enum_column(AssetClass, "asset_class"), nullable=False
    )
    currency_code: Mapped[str | None] = mapped_column(String(3))
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "asset_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class Underlying(UuidMixin, TimestampMixin, Base):
    __tablename__ = "underlyings"
    __table_args__ = (UniqueConstraint("code", name="uq_underlyings_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    primary_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_class: Mapped[AssetClass] = mapped_column(
        enum_column(AssetClass, "underlying_asset_class"), nullable=False
    )
    country_code: Mapped[str | None] = mapped_column(String(2))
    sector: Mapped[str | None] = mapped_column(String(80))
    industry: Mapped[str | None] = mapped_column(String(120))
    themes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "underlying_status"), default=RecordStatus.ACTIVE, nullable=False
    )

    primary_asset: Mapped[Asset] = relationship()


class Instrument(UuidMixin, TimestampMixin, Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("code", name="uq_instruments_code"),
        CheckConstraint("tick_size > 0", name="ck_instruments_tick_size_positive"),
        CheckConstraint("lot_size > 0", name="ck_instruments_lot_size_positive"),
        CheckConstraint("contract_multiplier > 0", name="ck_instruments_multiplier_positive"),
        CheckConstraint(
            "max_leverage IS NULL OR max_leverage >= 1", name="ck_instruments_leverage"
        ),
    )

    code: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    underlying_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    base_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quote_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    settlement_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    instrument_type: Mapped[InstrumentType] = mapped_column(
        enum_column(InstrumentType, "instrument_type"), nullable=False
    )
    tick_size: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    lot_size: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    contract_multiplier: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    max_leverage: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    shortable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    session_name: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "instrument_status"), default=RecordStatus.ACTIVE, nullable=False
    )

    underlying: Mapped[Underlying] = relationship()
    base_asset: Mapped[Asset] = relationship(foreign_keys=[base_asset_id])
    quote_asset: Mapped[Asset] = relationship(foreign_keys=[quote_asset_id])
    settlement_asset: Mapped[Asset] = relationship(foreign_keys=[settlement_asset_id])


class Venue(UuidMixin, TimestampMixin, Base):
    __tablename__ = "venues"
    __table_args__ = (UniqueConstraint("code", name="uq_venues_code"),)

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "venue_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class VenueInstrument(UuidMixin, TimestampMixin, Base):
    __tablename__ = "venue_instruments"
    __table_args__ = (
        UniqueConstraint("venue_id", "symbol", name="uq_venue_instruments_symbol"),
        UniqueConstraint("venue_id", "instrument_id", name="uq_venue_instruments_mapping"),
        Index("ix_venue_instruments_lookup", "venue_id", "symbol", "status"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "venue_instrument_status"),
        default=RecordStatus.ACTIVE,
        nullable=False,
    )

    venue: Mapped[Venue] = relationship()
    instrument: Mapped[Instrument] = relationship()


class Portfolio(UuidMixin, TimestampMixin, Base):
    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("code", name="uq_portfolios_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "portfolio_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class Account(UuidMixin, TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint(
            "venue_id", "environment", "external_reference", name="uq_accounts_external"
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    environment: Mapped[Environment] = mapped_column(
        enum_column(Environment, "account_environment"), nullable=False
    )
    external_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "account_status"), default=RecordStatus.ACTIVE, nullable=False
    )

    venue: Mapped[Venue] = relationship()
    portfolio: Mapped[Portfolio] = relationship()


class Strategy(UuidMixin, TimestampMixin, Base):
    __tablename__ = "strategies"
    __table_args__ = (UniqueConstraint("code", name="uq_strategies_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[RecordStatus] = mapped_column(
        enum_column(RecordStatus, "strategy_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class StrategyVersion(UuidMixin, TimestampMixin, Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (
        UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_version"),
        UniqueConstraint("strategy_id", "code_hash", name="uq_strategy_versions_hash"),
    )

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[StrategyState] = mapped_column(
        enum_column(StrategyState, "strategy_version_state"),
        default=StrategyState.DEVELOPMENT,
        nullable=False,
    )

    strategy: Mapped[Strategy] = relationship()
