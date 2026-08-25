from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MarketDataStatus(StrEnum):
    VALID = "VALID"
    STALE = "STALE"
    INVALID = "INVALID"


class MarketDataPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_age_seconds: int = Field(gt=0)
    maximum_future_skew_seconds: int = Field(ge=0)
    maximum_spread_pct: Decimal = Field(gt=0)
    maximum_price_jump_pct: Decimal = Field(gt=0)


class QuoteInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: uuid.UUID
    venue_code: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=64)
    source_timestamp: datetime
    received_at: datetime
    bid: Decimal = Field(gt=0)
    ask: Decimal = Field(gt=0)
    last: Decimal | None = Field(default=None, gt=0)
    volume: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_timestamps(self) -> QuoteInput:
        if self.source_timestamp.tzinfo is None or self.received_at.tzinfo is None:
            raise ValueError("market-data timestamps must include a timezone")
        return self


class OhlcvInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: uuid.UUID
    venue_code: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=64)
    timeframe: str = Field(min_length=1, max_length=16)
    open_time: datetime
    close_time: datetime
    received_at: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_bar(self) -> OhlcvInput:
        timestamps = (self.open_time, self.close_time, self.received_at)
        if any(value.tzinfo is None for value in timestamps):
            raise ValueError("market-data timestamps must include a timezone")
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be later than open_time")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC values are inconsistent with the high/low range")
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        return self


class QuoteAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: MarketDataStatus
    mid: Decimal
    spread: Decimal
    spread_pct: Decimal
    age_seconds: Decimal
    reasons: list[str]


class QuoteRead(QuoteInput):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mid: Decimal
    spread: Decimal
    spread_pct: Decimal
    age_seconds: Decimal
    status: MarketDataStatus
    reasons: list[str]


class OhlcvRead(OhlcvInput):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
