from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class CapitalPoolLedger(UuidMixin, TimestampMixin, Base):
    __tablename__ = "capital_pool_ledgers"
    pool_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    allocated_capital: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    investor_units: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    metadata_values: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class AdvancedExecutionPlanRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "advanced_execution_plans"
    order_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    style: Mapped[str] = mapped_column(String(32), nullable=False)
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    slices: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)


class PortfolioAnalyticsRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_analytics"
    portfolio_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value_at_risk: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    expected_shortfall: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    analytics: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class NativeStrategySignalRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "native_strategy_signals"
    strategy_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    direction: Mapped[int] = mapped_column(nullable=False)
    specification_version: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(String(160), nullable=False)


class SignalAuthorityRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "signal_authority_decisions"
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    production_authority_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tradingview_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
