from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class StrategyPerformanceRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "strategy_performance_assessments"
    strategy_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    breaches: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class StressTestRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "stress_test_results"
    scenario: Mapped[str] = mapped_column(String(120), nullable=False)
    projected_loss: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    projected_loss_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    contributors: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class EventRiskRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "event_risk_decisions"
    event_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entries_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_multiplier: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)


class ShadowLiveRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "shadow_live_runs"
    signal_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    hypothetical_notional: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    sent_to_venue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class LiveReadinessReviewRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "live_readiness_reviews"
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failed_checks: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
