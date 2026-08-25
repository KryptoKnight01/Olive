from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from olive.config import get_settings
from olive.db import get_session
from olive.market_data.schemas import (
    MarketDataPolicy,
    OhlcvInput,
    OhlcvRead,
    QuoteInput,
    QuoteRead,
)
from olive.market_data.service import MarketDataService

router = APIRouter(prefix="/api/v1/market-data", tags=["market-data"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def service(session: AsyncSession) -> MarketDataService:
    settings = get_settings()
    policy = MarketDataPolicy(
        maximum_age_seconds=settings.market_data_max_age_seconds,
        maximum_future_skew_seconds=settings.market_data_max_future_skew_seconds,
        maximum_spread_pct=settings.market_data_max_spread_pct,
        maximum_price_jump_pct=settings.market_data_max_price_jump_pct,
    )
    return MarketDataService(session, policy)


@router.post("/quotes", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def ingest_quote(data: QuoteInput, session: SessionDependency) -> QuoteRead:
    record = await service(session).ingest_quote(data, evaluated_at=datetime.now(UTC))
    return QuoteRead.model_validate(record)


@router.get("/quotes/{instrument_id}/latest", response_model=QuoteRead)
async def latest_quote(instrument_id: uuid.UUID, session: SessionDependency) -> QuoteRead:
    return QuoteRead.model_validate(await service(session).latest_quote(instrument_id))


@router.post("/ohlcv", response_model=OhlcvRead, status_code=status.HTTP_201_CREATED)
async def ingest_ohlcv(data: OhlcvInput, session: SessionDependency) -> OhlcvRead:
    return OhlcvRead.model_validate(await service(session).ingest_ohlcv(data))
