from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CapitalPool(BaseModel):
    model_config = ConfigDict(frozen=True)
    pool_key: str
    allocated_capital: Decimal = Field(gt=0)
    reserved_capital: Decimal = Field(ge=0)
    investor_units: Decimal = Field(gt=0)


class PoolAllocation(BaseModel):
    model_config = ConfigDict(frozen=True)
    pool_key: str
    approved_notional: Decimal
    available_capital: Decimal
    unit_value: Decimal
    reason: str


class ExecutionStyle(StrEnum):
    TWAP = "TWAP"
    VWAP = "VWAP"
    ADAPTIVE_LIMIT = "ADAPTIVE_LIMIT"


class ExecutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    order_id: str
    total_quantity: Decimal = Field(gt=0)
    duration_minutes: int = Field(gt=0)
    slices: int = Field(gt=0)
    reference_price: Decimal = Field(gt=0)
    max_participation_pct: Decimal = Field(gt=0, le=100)


class ExecutionSlice(BaseModel):
    model_config = ConfigDict(frozen=True)
    sequence: int
    minute_offset: int
    quantity: Decimal
    limit_price: Decimal


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    order_id: str
    style: ExecutionStyle
    slices: tuple[ExecutionSlice, ...]
    total_quantity: Decimal


class PortfolioAnalyticsInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    portfolio_value: Decimal = Field(gt=0)
    position_values: dict[str, Decimal]
    returns: dict[str, tuple[Decimal, ...]]
    confidence_pct: Decimal = Decimal("95")


class PortfolioAnalytics(BaseModel):
    model_config = ConfigDict(frozen=True)
    value_at_risk: Decimal
    expected_shortfall: Decimal
    risk_contribution: dict[str, Decimal]
    covariance: dict[str, dict[str, Decimal]]


class StrategyBar(BaseModel):
    model_config = ConfigDict(frozen=True)
    close: Decimal = Field(gt=0)
    fast_average: Decimal = Field(gt=0)
    slow_average: Decimal = Field(gt=0)


class NativeSignal(BaseModel):
    model_config = ConfigDict(frozen=True)
    strategy_key: str
    direction: int = Field(ge=-1, le=1)
    reason: str
    specification_version: str


class ParityResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    samples: int
    matches: int
    parity_pct: Decimal
    passed: bool


class SignalAuthority(StrEnum):
    TRADINGVIEW = "TRADINGVIEW"
    PARALLEL = "PARALLEL"
    NATIVE_PYTHON = "NATIVE_PYTHON"


class AuthorityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    authority: SignalAuthority = SignalAuthority.TRADINGVIEW
    minimum_parity_pct: Decimal = Decimal("99")
    observed_parity_pct: Decimal = Decimal("0")
    review_approved: bool = False


class AuthorityDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: SignalAuthority
    production_authority_granted: bool
    tradingview_required: bool
    reasons: tuple[str, ...]
