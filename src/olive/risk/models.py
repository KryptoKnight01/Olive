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


class PortfolioRiskPolicyRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_risk_policies"
    __table_args__ = (
        UniqueConstraint("scope_key", name="uq_portfolio_risk_policy_scope"),
        CheckConstraint("max_concurrent_positions > 0", name="ck_portfolio_positions_positive"),
        CheckConstraint("max_leverage >= 1", name="ck_portfolio_risk_leverage"),
    )

    scope_key: Mapped[str] = mapped_column(String(100), nullable=False)
    max_gross_exposure_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    max_net_exposure_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    max_long_exposure_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    max_short_exposure_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    max_open_stop_risk_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    max_margin_utilization_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    max_leverage: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    max_concurrent_positions: Mapped[int] = mapped_column(nullable=False)


class PortfolioRiskDecisionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_risk_decisions"
    __table_args__ = (
        UniqueConstraint("trade_risk_decision_id", name="uq_portfolio_decision_trade_risk"),
    )

    trade_risk_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trade_risk_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    portfolio_risk_policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio_risk_policies.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    approved_fraction: Mapped[Decimal] = mapped_column(Numeric(18, 12), nullable=False)
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    current_snapshot: Mapped[dict[str, str | int]] = mapped_column(JSON, nullable=False)
    projected_snapshot: Mapped[dict[str, str | int]] = mapped_column(JSON, nullable=False)
    limits: Mapped[dict[str, str | int]] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    @property
    def outcome(self) -> RiskDecisionOutcome:
        return RiskDecisionOutcome(self.decision)


class HierarchicalExposureLimitRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "hierarchical_exposure_limits"
    __table_args__ = (
        UniqueConstraint(
            "configuration_version",
            "dimension",
            "scope_key",
            "metric",
            name="uq_hierarchical_limit_identity",
        ),
        CheckConstraint("maximum > 0", name="ck_hierarchical_limit_positive"),
    )

    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(200), nullable=False)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    maximum: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)


class HierarchicalRiskDecisionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "hierarchical_risk_decisions"
    __table_args__ = (
        UniqueConstraint("portfolio_risk_decision_id", name="uq_hierarchy_decision_portfolio"),
    )

    portfolio_risk_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio_risk_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    approved_fraction: Mapped[Decimal] = mapped_column(Numeric(18, 12), nullable=False)
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    binding_limit: Mapped[str | None] = mapped_column(String(500))
    evaluations: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    @property
    def outcome(self) -> RiskDecisionOutcome:
        return RiskDecisionOutcome(self.decision)


class CorrelationRiskPolicyRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "correlation_risk_policies"
    __table_args__ = (
        UniqueConstraint("configuration_version", name="uq_correlation_policy_version"),
        CheckConstraint("minimum_observations >= 3", name="ck_correlation_minimum_history"),
        CheckConstraint(
            "lookback_observations >= minimum_observations", name="ck_correlation_lookback"
        ),
    )

    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    lookback_observations: Mapped[int] = mapped_column(nullable=False)
    minimum_observations: Mapped[int] = mapped_column(nullable=False)
    cluster_threshold: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    max_correlated_positions: Mapped[int] = mapped_column(nullable=False)
    max_cluster_stop_risk: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)


class CorrelationRiskDecisionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "correlation_risk_decisions"
    __table_args__ = (
        UniqueConstraint("hierarchical_risk_decision_id", name="uq_correlation_decision_hierarchy"),
    )

    hierarchical_risk_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hierarchical_risk_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    correlation_risk_policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("correlation_risk_policies.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    approved_fraction: Mapped[Decimal] = mapped_column(Numeric(18, 12), nullable=False)
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    proposed_cluster: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    correlations: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    cluster_position_count: Mapped[int] = mapped_column(nullable=False)
    current_cluster_stop_risk: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    projected_cluster_stop_risk: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    @property
    def outcome(self) -> RiskDecisionOutcome:
        return RiskDecisionOutcome(self.decision)
