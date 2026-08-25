from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ExecutionRiskAction(StrEnum):
    APPROVE = "APPROVE"
    REDUCE = "REDUCE"
    SPLIT = "SPLIT"
    DEFER = "DEFER"
    REJECT = "REJECT"


class ExecutionRiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_spread_pct: Decimal = Field(gt=0)
    maximum_slippage_pct: Decimal = Field(gt=0)
    maximum_adv_participation_pct: Decimal = Field(gt=0, le=100)
    maximum_book_participation_pct: Decimal = Field(gt=0, le=100)
    minimum_executable_notional: Decimal = Field(gt=0)
    minimum_reduced_fraction: Decimal = Field(gt=0, le=1)
    maximum_slices: int = Field(gt=1)


class ExecutionRiskInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    market_quote_id: uuid.UUID
    requested_quantity: Decimal = Field(gt=0)
    requested_notional: Decimal = Field(gt=0)
    spread_pct: Decimal = Field(ge=0)
    expected_slippage_pct: Decimal = Field(ge=0)
    average_daily_volume_notional: Decimal = Field(gt=0)
    available_book_notional: Decimal = Field(gt=0)
    market_data_status: str


class ExecutionRiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    action: ExecutionRiskAction
    requested_quantity: Decimal
    approved_quantity: Decimal
    requested_notional: Decimal
    approved_notional: Decimal
    maximum_executable_notional: Decimal
    slice_count: int
    binding_limits: list[str]
    reasons: list[str]
