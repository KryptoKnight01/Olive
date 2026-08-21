from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from olive.db import get_session
from olive.domain.schemas import (
    AssetCreate,
    AssetRead,
    InstrumentCreate,
    InstrumentRead,
    ResolvedInstrument,
    UnderlyingCreate,
    UnderlyingRead,
    VenueCreate,
    VenueInstrumentCreate,
    VenueInstrumentRead,
    VenueRead,
)
from olive.domain.services import AssetMasterService

router = APIRouter(prefix="/api/v1/asset-master", tags=["asset-master"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(data: AssetCreate, session: SessionDependency) -> AssetRead:
    return AssetRead.model_validate(await AssetMasterService(session).create_asset(data))


@router.get("/assets", response_model=list[AssetRead])
async def list_assets(session: SessionDependency) -> list[AssetRead]:
    assets = await AssetMasterService(session).list_assets()
    return [AssetRead.model_validate(asset) for asset in assets]


@router.post("/underlyings", response_model=UnderlyingRead, status_code=status.HTTP_201_CREATED)
async def create_underlying(data: UnderlyingCreate, session: SessionDependency) -> UnderlyingRead:
    return UnderlyingRead.model_validate(await AssetMasterService(session).create_underlying(data))


@router.post("/instruments", response_model=InstrumentRead, status_code=status.HTTP_201_CREATED)
async def create_instrument(data: InstrumentCreate, session: SessionDependency) -> InstrumentRead:
    return InstrumentRead.model_validate(await AssetMasterService(session).create_instrument(data))


@router.post("/venues", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
async def create_venue(data: VenueCreate, session: SessionDependency) -> VenueRead:
    return VenueRead.model_validate(await AssetMasterService(session).create_venue(data))


@router.post(
    "/venue-instruments",
    response_model=VenueInstrumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_venue_instrument(
    data: VenueInstrumentCreate, session: SessionDependency
) -> VenueInstrumentRead:
    return VenueInstrumentRead.model_validate(
        await AssetMasterService(session).create_venue_instrument(data)
    )


@router.get("/resolve", response_model=ResolvedInstrument)
async def resolve_venue_symbol(
    session: SessionDependency,
    venue_code: str = Query(min_length=1, max_length=32),
    symbol: str = Query(min_length=1, max_length=96),
) -> ResolvedInstrument:
    return await AssetMasterService(session).resolve(venue_code, symbol)
