from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin
from olive.risk.schemas import RiskDecisionOutcome


class SingleTradeRiskPolicyRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "single_trade_risk_policies"
    __table_args__ = (
        UniqueConstraint("strategy_version_id", name="uq_trade_risk_policy_version"),
        CheckConstraint("base_risk_pct > 0", name="ck_trade_risk_base_positive"),
        CheckConstraint("max_risk_pct > 0", name="ck_trade_risk_max_positive"),
        CheckConstraint("max_notional > 0", name="ck_trade_risk_notional_positive"),
        CheckConstraint("max_leverage >= 1", name="ck_trade_risk_leverage"),
        CheckConstraint("max_margin > 0", name="ck_trade_risk_margin_positive"),
    )

    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False
    )
    base_risk_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    max_risk_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    max_notional: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    max_leverage: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    max_margin: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    min_stop_distance_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    max_stop_distance_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)


class TradeRiskDecisionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "trade_risk_decisions"
    __table_args__ = (UniqueConstraint("signal_intake_id", name="uq_trade_risk_decision_signal"),)

    signal_intake_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("signal_intake_records.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_risk_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    approved_risk_pct: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    position_size: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    base_risk_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    equity_snapshot: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    available_margin_snapshot: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    multipliers: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    limits: Mapped[dict[str, str | None]] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    @property
    def outcome(self) -> RiskDecisionOutcome:
        return RiskDecisionOutcome(self.decision)
