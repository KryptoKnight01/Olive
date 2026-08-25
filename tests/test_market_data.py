from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from olive.market_data.quality import MarketDataQualityEngine
from olive.market_data.schemas import (
    MarketDataPolicy,
    MarketDataStatus,
    OhlcvInput,
    QuoteInput,
)

NOW = datetime(2026, 8, 25, 12, tzinfo=UTC)
POLICY = MarketDataPolicy(
    maximum_age_seconds=10,
    maximum_future_skew_seconds=2,
    maximum_spread_pct=Decimal("2"),
    maximum_price_jump_pct=Decimal("5"),
)


def quote(**changes: object) -> QuoteInput:
    values: dict[str, object] = {
        "instrument_id": uuid.uuid4(),
        "venue_code": "COINBASE",
        "source": "sandbox-feed",
        "source_timestamp": NOW - timedelta(seconds=1),
        "received_at": NOW,
        "bid": Decimal("99"),
        "ask": Decimal("100"),
        "last": Decimal("99.5"),
        "volume": Decimal("12"),
    }
    values.update(changes)
    return QuoteInput.model_validate(values)


def test_normalizes_valid_quote_and_calculates_spread() -> None:
    result = MarketDataQualityEngine().assess_quote(quote(), POLICY, evaluated_at=NOW)

    assert result.status is MarketDataStatus.VALID
    assert result.mid == Decimal("99.5")
    assert result.spread == Decimal("1")
    assert result.age_seconds == Decimal("1.0")


def test_marks_old_quote_stale() -> None:
    result = MarketDataQualityEngine().assess_quote(
        quote(source_timestamp=NOW - timedelta(seconds=11)), POLICY, evaluated_at=NOW
    )

    assert result.status is MarketDataStatus.STALE
    assert "maximum age" in result.reasons[0]


def test_rejects_crossed_market() -> None:
    result = MarketDataQualityEngine().assess_quote(
        quote(bid=Decimal("101"), ask=Decimal("100")), POLICY, evaluated_at=NOW
    )

    assert result.status is MarketDataStatus.INVALID
    assert "below bid" in result.reasons[0]


def test_rejects_excessive_spread() -> None:
    result = MarketDataQualityEngine().assess_quote(
        quote(bid=Decimal("90"), ask=Decimal("100")), POLICY, evaluated_at=NOW
    )

    assert result.status is MarketDataStatus.INVALID
    assert any("spread" in reason for reason in result.reasons)


def test_rejects_price_jump_against_previous_quote() -> None:
    result = MarketDataQualityEngine().assess_quote(
        quote(bid=Decimal("109"), ask=Decimal("111")),
        POLICY,
        evaluated_at=NOW,
        previous_mid=Decimal("100"),
    )

    assert result.status is MarketDataStatus.INVALID
    assert any("price jump" in reason for reason in result.reasons)


def test_rejects_future_timestamp_beyond_clock_tolerance() -> None:
    result = MarketDataQualityEngine().assess_quote(
        quote(source_timestamp=NOW + timedelta(seconds=3)), POLICY, evaluated_at=NOW
    )

    assert result.status is MarketDataStatus.INVALID
    assert any("future" in reason for reason in result.reasons)


def test_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        quote(source_timestamp=datetime(2026, 8, 25, 12))


def test_rejects_inconsistent_ohlcv_bar() -> None:
    with pytest.raises(ValidationError, match="OHLC"):
        OhlcvInput(
            instrument_id=uuid.uuid4(),
            venue_code="COINBASE",
            source="sandbox-feed",
            timeframe="1m",
            open_time=NOW - timedelta(minutes=1),
            close_time=NOW,
            received_at=NOW,
            open=Decimal("100"),
            high=Decimal("99"),
            low=Decimal("95"),
            close=Decimal("98"),
            volume=Decimal("10"),
        )
