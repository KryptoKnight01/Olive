from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class MarketQuoteRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "market_quotes"
    __table_args__ = (
        Index("ix_market_quotes_instrument_source_time", "instrument_id", "source_timestamp"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    venue_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bid: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    ask: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    last: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    mid: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    spread: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    spread_pct: Mapped[Decimal] = mapped_column(Numeric(18, 12), nullable=False)
    age_seconds: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class OhlcvRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "market_ohlcv"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "venue_code", "source", "timeframe", "open_time",
            name="uq_market_ohlcv_bar",
        ),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    venue_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
