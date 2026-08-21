from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from olive.db import Base
from olive.domain.errors import DomainConflict, DomainNotFound, DomainValidationError
from olive.domain.models import Asset, Instrument, Underlying, Venue, VenueInstrument
from olive.domain.schemas import (
    AssetCreate,
    InstrumentCreate,
    ResolvedInstrument,
    UnderlyingCreate,
    VenueCreate,
    VenueInstrumentCreate,
)

ModelT = TypeVar("ModelT", bound=Base)


class AssetMasterService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_asset(self, data: AssetCreate) -> Asset:
        await self._ensure_code_available(Asset, Asset.code, data.code, "asset")
        asset = Asset(**data.model_dump())
        self._session.add(asset)
        await self._save()
        return asset

    async def list_assets(self) -> list[Asset]:
        result = await self._session.scalars(select(Asset).order_by(Asset.code))
        return list(result)

    async def create_underlying(self, data: UnderlyingCreate) -> Underlying:
        await self._ensure_code_available(Underlying, Underlying.code, data.code, "underlying")
        asset = await self._get(Asset, data.primary_asset_id, "primary asset")
        if asset.asset_class != data.asset_class:
            raise DomainValidationError("underlying asset class must match its primary asset class")
        underlying = Underlying(**data.model_dump())
        self._session.add(underlying)
        await self._save()
        return underlying

    async def create_instrument(self, data: InstrumentCreate) -> Instrument:
        await self._ensure_code_available(Instrument, Instrument.code, data.code, "instrument")
        underlying = await self._get(Underlying, data.underlying_id, "underlying")
        if underlying.primary_asset_id != data.base_asset_id:
            raise DomainValidationError(
                "instrument base asset must match the underlying primary asset"
            )
        for asset_id, label in (
            (data.base_asset_id, "base asset"),
            (data.quote_asset_id, "quote asset"),
            (data.settlement_asset_id, "settlement asset"),
        ):
            await self._get(Asset, asset_id, label)
        instrument = Instrument(**data.model_dump())
        self._session.add(instrument)
        await self._save()
        return instrument

    async def create_venue(self, data: VenueCreate) -> Venue:
        await self._ensure_code_available(Venue, Venue.code, data.code, "venue")
        venue = Venue(**data.model_dump())
        self._session.add(venue)
        await self._save()
        return venue

    async def create_venue_instrument(self, data: VenueInstrumentCreate) -> VenueInstrument:
        await self._get(Venue, data.venue_id, "venue")
        await self._get(Instrument, data.instrument_id, "instrument")
        existing_symbol = await self._session.scalar(
            select(VenueInstrument).where(
                VenueInstrument.venue_id == data.venue_id,
                VenueInstrument.symbol == data.symbol,
            )
        )
        if existing_symbol is not None:
            raise DomainConflict("venue symbol is already mapped")
        existing_mapping = await self._session.scalar(
            select(VenueInstrument).where(
                VenueInstrument.venue_id == data.venue_id,
                VenueInstrument.instrument_id == data.instrument_id,
            )
        )
        if existing_mapping is not None:
            raise DomainConflict("instrument is already mapped for this venue")
        mapping = VenueInstrument(**data.model_dump())
        self._session.add(mapping)
        await self._save()
        return mapping

    async def resolve(self, venue_code: str, symbol: str) -> ResolvedInstrument:
        row = (
            await self._session.execute(
                select(VenueInstrument, Venue, Instrument, Underlying)
                .join(Venue, Venue.id == VenueInstrument.venue_id)
                .join(Instrument, Instrument.id == VenueInstrument.instrument_id)
                .join(Underlying, Underlying.id == Instrument.underlying_id)
                .where(Venue.code == venue_code.upper(), VenueInstrument.symbol == symbol.upper())
            )
        ).one_or_none()
        if row is None:
            raise DomainNotFound("venue symbol mapping was not found")
        mapping, venue, instrument, underlying = row
        return ResolvedInstrument(
            mapping_id=mapping.id,
            venue_id=venue.id,
            venue_code=venue.code,
            venue_symbol=mapping.symbol,
            instrument_id=instrument.id,
            instrument_code=instrument.code,
            underlying_id=underlying.id,
            underlying_code=underlying.code,
            status=mapping.status,
        )

    async def _ensure_code_available(
        self,
        model: type[ModelT],
        code_column: InstrumentedAttribute[str],
        code: str,
        label: str,
    ) -> None:
        existing = await self._session.scalar(select(model).where(code_column == code))
        if existing is not None:
            raise DomainConflict(f"{label} code already exists")

    async def _get(self, model: type[ModelT], identifier: uuid.UUID, label: str) -> ModelT:
        entity = await self._session.get(model, identifier)
        if entity is None:
            raise DomainNotFound(f"{label} was not found")
        return entity

    async def _save(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DomainConflict("record conflicts with an existing canonical identity") from exc
