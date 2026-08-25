from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ProductionMode(StrEnum):
    DISARMED = "DISARMED"
    LIMITED_LIVE = "LIMITED_LIVE"


class LiveCapitalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: ProductionMode = ProductionMode.DISARMED
    approved_strategy: str
    approved_instruments: frozenset[str]
    approved_venue: str
    max_order_notional: Decimal = Field(gt=0)
    max_total_exposure: Decimal = Field(gt=0)
    max_leverage: Decimal = Field(gt=0)
    readiness_approved: bool = False
    operator_armed: bool = False


class LiveOrderRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    strategy_key: str
    instrument: str
    venue: str
    requested_notional: Decimal = Field(gt=0)
    projected_total_exposure: Decimal = Field(ge=0)
    projected_leverage: Decimal = Field(ge=0)


class LiveCapitalDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    approved: bool
    approved_notional: Decimal
    route_permitted: bool
    reasons: tuple[str, ...]


class ExecutionObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    paper_delay_ms: int = Field(ge=0)
    live_delay_ms: int = Field(ge=0)
    paper_fill_price: Decimal = Field(gt=0)
    live_fill_price: Decimal | None = None
    paper_fee: Decimal = Field(ge=0)
    live_fee: Decimal = Field(ge=0)
    paper_pnl: Decimal
    live_pnl: Decimal


class DeviationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    delay_delta_ms: int
    slippage_pct: Decimal | None
    fee_delta: Decimal
    pnl_divergence: Decimal
    missed_fill: bool
    breached: bool
    reasons: tuple[str, ...]


class VenueQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue: str
    price: Decimal = Field(gt=0)
    available_notional: Decimal = Field(ge=0)
    fee_pct: Decimal = Field(ge=0)
    healthy: bool = True


class VenueSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue: str | None
    approved_notional: Decimal
    effective_price: Decimal | None
    reason: str


class VenueExposure(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue: str
    gross_exposure: Decimal = Field(ge=0)


class StrategySignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_key: str
    instrument: str
    direction: int = Field(ge=-1, le=1)
    priority: int = Field(ge=0)
    requested_risk_pct: Decimal = Field(ge=0)


class StrategyAllocation(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_key: str
    approved_risk_pct: Decimal
    accepted: bool
    reason: str


class StrategyResolution(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument: str
    direction: int
    allocations: tuple[StrategyAllocation, ...]
    total_risk_pct: Decimal


class AssetProductionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_class: str
    approved_instruments: frozenset[str]
    approved_venues: frozenset[str]
    max_notional: Decimal = Field(gt=0)
    enabled: bool = False


class AssetEligibilityDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    eligible: bool
    approved_notional: Decimal
    reasons: tuple[str, ...]
