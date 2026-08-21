from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from olive.domain.models import AssetClass, InstrumentType, RecordStatus


class DomainSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def normalize_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("code must not be blank")
    return normalized


class AssetCreate(DomainSchema):
    code: str = Field(max_length=32)
    name: str = Field(min_length=1, max_length=160)
    asset_class: AssetClass
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)

    _normalize_code = field_validator("code")(normalize_code)

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class AssetRead(AssetCreate):
    id: uuid.UUID
    status: RecordStatus


class UnderlyingCreate(DomainSchema):
    code: str = Field(max_length=64)
    name: str = Field(min_length=1, max_length=160)
    primary_asset_id: uuid.UUID
    asset_class: AssetClass
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    sector: str | None = Field(default=None, max_length=80)
    industry: str | None = Field(default=None, max_length=120)
    themes: list[str] = Field(default_factory=list, max_length=50)

    _normalize_code = field_validator("code")(normalize_code)

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class UnderlyingRead(UnderlyingCreate):
    id: uuid.UUID
    status: RecordStatus


class InstrumentCreate(DomainSchema):
    code: str = Field(max_length=96)
    name: str = Field(min_length=1, max_length=200)
    underlying_id: uuid.UUID
    base_asset_id: uuid.UUID
    quote_asset_id: uuid.UUID
    settlement_asset_id: uuid.UUID
    instrument_type: InstrumentType
    tick_size: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    lot_size: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    contract_multiplier: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    max_leverage: Decimal | None = Field(default=None, ge=1, max_digits=12, decimal_places=4)
    shortable: bool = False
    session_name: str | None = Field(default=None, max_length=80)

    _normalize_code = field_validator("code")(normalize_code)


class InstrumentRead(InstrumentCreate):
    id: uuid.UUID
    status: RecordStatus


class VenueCreate(DomainSchema):
    code: str = Field(max_length=32)
    name: str = Field(min_length=1, max_length=160)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)

    _normalize_code = field_validator("code")(normalize_code)


class VenueRead(VenueCreate):
    id: uuid.UUID
    status: RecordStatus


class VenueInstrumentCreate(DomainSchema):
    venue_id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: str = Field(min_length=1, max_length=96)

    _normalize_symbol = field_validator("symbol")(normalize_code)


class VenueInstrumentRead(VenueInstrumentCreate):
    id: uuid.UUID
    status: RecordStatus


class ResolvedInstrument(DomainSchema):
    mapping_id: uuid.UUID
    venue_id: uuid.UUID
    venue_code: str
    venue_symbol: str
    instrument_id: uuid.UUID
    instrument_code: str
    underlying_id: uuid.UUID
    underlying_code: str
    status: RecordStatus
