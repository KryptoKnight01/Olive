from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RiskDecisionOutcome(StrEnum):
    APPROVED = "APPROVED"
    APPROVED_WITH_REDUCED_SIZE = "APPROVED_WITH_REDUCED_SIZE"
    REJECTED = "REJECTED"


class SingleTradeRiskInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    equity: Decimal = Field(gt=0)
    available_margin: Decimal = Field(ge=0)
    entry_price: Decimal = Field(gt=0)
    stop_price: Decimal = Field(gt=0)
    requested_risk_pct: Decimal = Field(gt=0)
    contract_multiplier: Decimal = Field(gt=0)
    lot_size: Decimal = Field(gt=0)
    instrument_max_leverage: Decimal | None = Field(default=None, ge=1)


class SingleTradeRiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_risk_pct: Decimal = Field(gt=0)
    max_risk_pct: Decimal = Field(gt=0)
    max_notional: Decimal = Field(gt=0)
    max_leverage: Decimal = Field(ge=1)
    max_margin: Decimal = Field(gt=0)
    min_stop_distance_pct: Decimal = Field(gt=0)
    max_stop_distance_pct: Decimal = Field(gt=0)


class SingleTradeRiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: RiskDecisionOutcome
    signal_id: uuid.UUID
    requested_risk_pct: Decimal
    approved_risk_pct: Decimal
    position_size: Decimal
    base_risk_pct: Decimal
    multipliers: dict[str, Decimal]
    limits: dict[str, Decimal | None]
    reasons: list[str]


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class PortfolioPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    side: PositionSide
    notional: Decimal = Field(ge=0)
    stop_risk: Decimal = Field(ge=0)
    margin_used: Decimal = Field(ge=0)


class PortfolioRiskInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    equity: Decimal = Field(gt=0)
    proposed_side: PositionSide
    proposed_notional: Decimal = Field(gt=0)
    proposed_stop_risk: Decimal = Field(gt=0)
    proposed_margin: Decimal = Field(ge=0)
    positions: tuple[PortfolioPosition, ...] = ()


class PortfolioRiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_gross_exposure_pct: Decimal = Field(gt=0)
    max_net_exposure_pct: Decimal = Field(gt=0)
    max_long_exposure_pct: Decimal = Field(gt=0)
    max_short_exposure_pct: Decimal = Field(gt=0)
    max_open_stop_risk_pct: Decimal = Field(gt=0)
    max_margin_utilization_pct: Decimal = Field(gt=0, le=100)
    max_leverage: Decimal = Field(ge=1)
    max_concurrent_positions: int = Field(gt=0)


class PortfolioRiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: RiskDecisionOutcome
    signal_id: uuid.UUID
    approved_fraction: Decimal = Field(ge=0, le=1)
    approved_notional: Decimal = Field(ge=0)
    current: dict[str, Decimal | int]
    projected: dict[str, Decimal | int]
    limits: dict[str, Decimal | int]
    reasons: list[str]


class ExposureDimension(StrEnum):
    INSTRUMENT = "INSTRUMENT"
    UNDERLYING = "UNDERLYING"
    STRATEGY = "STRATEGY"
    ASSET_CLASS = "ASSET_CLASS"
    SECTOR = "SECTOR"
    INDUSTRY = "INDUSTRY"
    THEME = "THEME"
    VENUE = "VENUE"
    ACCOUNT = "ACCOUNT"
    PORTFOLIO = "PORTFOLIO"


class ExposureMetric(StrEnum):
    GROSS_NOTIONAL = "GROSS_NOTIONAL"
    OPEN_STOP_RISK = "OPEN_STOP_RISK"
    MARGIN_USED = "MARGIN_USED"
    POSITION_COUNT = "POSITION_COUNT"


class HierarchicalExposureLimit(BaseModel):
    model_config = ConfigDict(frozen=True)

    dimension: ExposureDimension
    scope_key: str = Field(min_length=1, max_length=200)
    metric: ExposureMetric
    maximum: Decimal = Field(gt=0)


class ExposurePosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    tags: dict[ExposureDimension, tuple[str, ...]]
    gross_notional: Decimal = Field(ge=0)
    open_stop_risk: Decimal = Field(ge=0)
    margin_used: Decimal = Field(ge=0)


class HierarchicalRiskInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    proposed_tags: dict[ExposureDimension, tuple[str, ...]]
    proposed_notional: Decimal = Field(gt=0)
    proposed_stop_risk: Decimal = Field(gt=0)
    proposed_margin: Decimal = Field(ge=0)
    positions: tuple[ExposurePosition, ...] = ()


class HierarchicalRiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: RiskDecisionOutcome
    signal_id: uuid.UUID
    approved_fraction: Decimal = Field(ge=0, le=1)
    approved_notional: Decimal = Field(ge=0)
    binding_limit: str | None
    evaluations: list[dict[str, str]]
    reasons: list[str]


class CorrelatedPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_key: str = Field(min_length=1, max_length=200)
    open_stop_risk: Decimal = Field(ge=0)


class CorrelationRiskInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    proposed_instrument_key: str = Field(min_length=1, max_length=200)
    proposed_notional: Decimal = Field(gt=0)
    proposed_stop_risk: Decimal = Field(gt=0)
    price_history: dict[str, tuple[Decimal, ...]]
    positions: tuple[CorrelatedPosition, ...] = ()


class CorrelationRiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    lookback_observations: int = Field(ge=3)
    minimum_observations: int = Field(ge=3)
    cluster_threshold: Decimal = Field(gt=0, le=1)
    max_correlated_positions: int = Field(gt=0)
    max_cluster_stop_risk: Decimal = Field(gt=0)


class CorrelationRiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: RiskDecisionOutcome
    signal_id: uuid.UUID
    approved_fraction: Decimal = Field(ge=0, le=1)
    approved_notional: Decimal = Field(ge=0)
    proposed_cluster: tuple[str, ...]
    correlations: dict[str, Decimal]
    current_cluster_positions: int
    current_cluster_stop_risk: Decimal
    projected_cluster_stop_risk: Decimal
    reasons: list[str]


class MultiplierBounds(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum: Decimal = Field(gt=0)
    maximum: Decimal = Field(gt=0)


class DynamicRiskInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    base_risk_pct: Decimal = Field(gt=0)
    hard_max_risk_pct: Decimal = Field(gt=0)
    regime: Decimal = Field(gt=0)
    correlation: Decimal = Field(gt=0)
    drawdown: Decimal = Field(gt=0)
    liquidity: Decimal = Field(gt=0)
    signal_quality: Decimal = Field(gt=0)
    strategy_health: Decimal = Field(gt=0)
    event_risk: Decimal = Field(gt=0)


class DynamicRiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    regime: MultiplierBounds
    correlation: MultiplierBounds
    drawdown: MultiplierBounds
    liquidity: MultiplierBounds
    signal_quality: MultiplierBounds
    strategy_health: MultiplierBounds
    event_risk: MultiplierBounds


class DynamicRiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    base_risk_pct: Decimal
    raw_multipliers: dict[str, Decimal]
    bounded_multipliers: dict[str, Decimal]
    multiplier_product: Decimal
    uncapped_risk_pct: Decimal
    final_risk_pct: Decimal
    caps: dict[str, Decimal]
    reasons: list[str]
