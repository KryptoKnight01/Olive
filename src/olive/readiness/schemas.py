from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"


class PerformanceMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_key: str
    profit_factor: Decimal
    win_rate: Decimal
    expectancy_r: Decimal
    average_r: Decimal
    max_drawdown_pct: Decimal
    trades: int = Field(ge=0)
    slippage_pct: Decimal = Decimal("0")
    average_holding_minutes: Decimal = Decimal("0")


class PerformanceThresholds(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_profit_factor: Decimal = Decimal("1.2")
    min_expectancy_r: Decimal = Decimal("0.1")
    max_drawdown_pct: Decimal = Decimal("15")
    max_slippage_pct: Decimal = Decimal("1")
    min_trades: int = 20


class PerformanceAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_key: str
    status: HealthStatus
    breaches: tuple[str, ...]


class StressScenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    volatility_multiplier: Decimal = Field(ge=0)
    correlation_multiplier: Decimal = Field(ge=0)
    liquidity_reduction_pct: Decimal = Field(ge=0, le=100)
    gap_pct: Decimal = Field(ge=0)
    venue_failure: bool = False


class StressInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    portfolio_value: Decimal = Field(gt=0)
    gross_exposure: Decimal = Field(ge=0)
    available_margin: Decimal = Field(ge=0)
    max_loss_pct: Decimal = Field(gt=0)


class StressResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario: str
    projected_loss: Decimal
    projected_loss_pct: Decimal
    margin_shortfall: Decimal
    blocked: bool
    contributors: tuple[str, ...]


class EventRiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    blackout_minutes_before: int = Field(ge=0)
    blackout_minutes_after: int = Field(ge=0)
    risk_multiplier: Decimal = Field(ge=0, le=1)
    allow_hold_through: bool = False


class EventObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_key: str
    minutes_from_event: int
    open_position: bool = False


class EventDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_key: str
    entries_allowed: bool
    risk_multiplier: Decimal
    close_before_event: bool
    reason: str


class ShadowOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    strategy_key: str
    instrument: str
    side: str
    quantity: Decimal = Field(gt=0)
    reference_price: Decimal = Field(gt=0)


class ShadowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    hypothetical_fill_price: Decimal
    hypothetical_notional: Decimal
    sent_to_venue: bool
    status: str


class ReadinessCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    evidence: str
    mandatory: bool = True


class ReadinessReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    approved: bool
    failed_checks: tuple[str, ...]
    checks: tuple[ReadinessCheck, ...]
