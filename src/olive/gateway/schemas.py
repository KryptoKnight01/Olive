from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from olive.domain.schemas import normalize_code
from olive.gateway.models import SignalDirection, SignalEnvironment, SignalIntakeStatus


class GatewaySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignalMetadata(GatewaySchema):
    atr: Decimal | None = Field(default=None, gt=0)
    volatility: Decimal | None = Field(default=None, ge=0)
    structure_state: str | None = Field(default=None, max_length=100)
    liquidity_target: str | None = Field(default=None, max_length=100)
    confirmation_state: str | None = Field(default=None, max_length=100)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    expected_holding_minutes: int | None = Field(default=None, gt=0, le=525600)
    entry_range_low: Decimal | None = Field(default=None, gt=0)
    entry_range_high: Decimal | None = Field(default=None, gt=0)


class SignalPayload(GatewaySchema):
    schema_version: str = Field(pattern=r"^1\.\d+$", max_length=16)
    signal_id: uuid.UUID
    strategy_id: str = Field(max_length=64)
    strategy_version: str = Field(min_length=1, max_length=64)
    configuration_version: str = Field(min_length=1, max_length=64)
    environment: SignalEnvironment
    timestamp: datetime
    expiry: datetime
    venue: str = Field(max_length=32)
    instrument: str = Field(max_length=96)
    direction: SignalDirection
    entry_price: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    reference_price: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    stop: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    targets: list[Decimal] = Field(min_length=1, max_length=10)
    expected_rr: Decimal = Field(ge=0, max_digits=18, decimal_places=8)
    timeframe: str = Field(min_length=1, max_length=32)
    setup_score: Decimal = Field(ge=0, le=100, max_digits=8, decimal_places=4)
    regime: str = Field(min_length=1, max_length=64)
    metadata: SignalMetadata | None = None

    _normalize_codes = field_validator("strategy_id", "venue", "instrument")(normalize_code)

    @field_validator("timestamp", "expiry")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(UTC)

    @field_validator("targets")
    @classmethod
    def targets_must_be_positive(cls, values: list[Decimal]) -> list[Decimal]:
        if any(value <= 0 for value in values):
            raise ValueError("targets must be positive")
        return values

    @model_validator(mode="after")
    def expiry_must_follow_timestamp(self) -> SignalPayload:
        if self.expiry <= self.timestamp:
            raise ValueError("expiry must be later than timestamp")
        return self


class SignalIntakeResponse(BaseModel):
    intake_id: uuid.UUID
    signal_id: uuid.UUID
    status: SignalIntakeStatus
