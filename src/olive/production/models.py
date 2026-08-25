from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class LiveCapitalDecisionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "live_capital_decisions"
    signal_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    route_permitted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class ExecutionDeviationRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "execution_deviation_reports"
    signal_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    delay_delta_ms: Mapped[int] = mapped_column(nullable=False)
    slippage_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    pnl_divergence: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    breached: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class VenueRouteDecisionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "venue_route_decisions"
    venue: Mapped[str | None] = mapped_column(String(120))
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    effective_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    reason: Mapped[str] = mapped_column(String(80), nullable=False)


class StrategyResolutionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "strategy_resolutions"
    instrument: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    direction: Mapped[int] = mapped_column(nullable=False)
    total_risk_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    allocations: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)


class AssetEligibilityRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "asset_eligibility_decisions"
    asset_class: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    instrument: Mapped[str] = mapped_column(String(120), nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
