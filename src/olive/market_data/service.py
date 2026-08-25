from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from olive.domain.models import Instrument
from olive.market_data.models import MarketQuoteRecord, OhlcvRecord
from olive.market_data.quality import MarketDataQualityEngine
from olive.market_data.schemas import MarketDataPolicy, OhlcvInput, QuoteInput


class MarketDataError(ValueError):
    pass


class MarketDataService:
    def __init__(self, session: AsyncSession, policy: MarketDataPolicy) -> None:
        self._session = session
        self._policy = policy

    async def ingest_quote(self, quote: QuoteInput, *, evaluated_at: datetime) -> MarketQuoteRecord:
        if await self._session.get(Instrument, quote.instrument_id) is None:
            raise MarketDataError("instrument was not found")
        previous = await self._session.scalar(
            select(MarketQuoteRecord)
            .where(MarketQuoteRecord.instrument_id == quote.instrument_id)
            .order_by(desc(MarketQuoteRecord.source_timestamp))
            .limit(1)
        )
        assessment = MarketDataQualityEngine().assess_quote(
            quote,
            self._policy,
            evaluated_at=evaluated_at,
            previous_mid=Decimal(previous.mid) if previous is not None else None,
        )
        record = MarketQuoteRecord(
            **quote.model_dump(),
            mid=assessment.mid,
            spread=assessment.spread,
            spread_pct=assessment.spread_pct,
            age_seconds=assessment.age_seconds,
            status=assessment.status.value,
            reasons=assessment.reasons,
        )
        self._session.add(record)
        await self._session.commit()
        return record

    async def ingest_ohlcv(self, bar: OhlcvInput) -> OhlcvRecord:
        if await self._session.get(Instrument, bar.instrument_id) is None:
            raise MarketDataError("instrument was not found")
        record = OhlcvRecord(**bar.model_dump())
        self._session.add(record)
        await self._session.commit()
        return record

    async def latest_quote(self, instrument_id: uuid.UUID) -> MarketQuoteRecord:
        record = await self._session.scalar(
            select(MarketQuoteRecord)
            .where(MarketQuoteRecord.instrument_id == instrument_id)
            .order_by(desc(MarketQuoteRecord.source_timestamp))
            .limit(1)
        )
        if record is None:
            raise MarketDataError("market quote was not found")
        return record
