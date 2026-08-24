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
