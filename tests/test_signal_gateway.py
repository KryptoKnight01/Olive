from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from olive.api.signal_gateway import get_signal_authenticator
from olive.db import Base, get_session
from olive.domain.models import (
    Asset,
    AssetClass,
    Instrument,
    InstrumentType,
    Strategy,
    StrategyVersion,
    Underlying,
    Venue,
    VenueInstrument,
)
from olive.gateway.auth import GatewayHeaders
from olive.gateway.errors import GatewayAuthenticationError
from olive.gateway.models import SignalIntakeRecord, SignalIntakeStatus
from olive.main import app


class AllowAuthenticator:
    async def authenticate(self, _body: bytes, _headers: GatewayHeaders) -> None:
        return None


class RejectAuthenticator:
    async def authenticate(self, _body: bytes, _headers: GatewayHeaders) -> None:
        raise GatewayAuthenticationError("invalid webhook credentials")


@dataclass
class GatewayTestContext:
    client: AsyncClient
    sessions: async_sessionmaker[AsyncSession]


@pytest.fixture
async def gateway_context() -> AsyncIterator[GatewayTestContext]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    await seed_reference_data(sessions)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_signal_authenticator] = AllowAuthenticator
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield GatewayTestContext(client=client, sessions=sessions)
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_signal_authenticator, None)
        await engine.dispose()


async def seed_reference_data(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions() as session:
        btc = Asset(code="BTC", name="Bitcoin", asset_class=AssetClass.CRYPTO)
        usd = Asset(code="USD", name="US Dollar", asset_class=AssetClass.CASH, currency_code="USD")
        session.add_all([btc, usd])
        await session.flush()
        underlying = Underlying(
            code="BTC",
            name="Bitcoin",
            primary_asset_id=btc.id,
            asset_class=AssetClass.CRYPTO,
        )
        venue = Venue(code="COINBASE", name="Coinbase")
        strategy = Strategy(code="OLC", name="Olive Liquidity Compass")
        session.add_all([underlying, venue, strategy])
        await session.flush()
        instrument = Instrument(
            code="BTC-USD-SPOT",
            name="Bitcoin / US Dollar Spot",
            underlying_id=underlying.id,
            base_asset_id=btc.id,
            quote_asset_id=usd.id,
            settlement_asset_id=usd.id,
            instrument_type=InstrumentType.SPOT,
            tick_size=Decimal("0.01"),
            lot_size=Decimal("0.00000001"),
            contract_multiplier=Decimal("1"),
        )
        version = StrategyVersion(
            strategy_id=strategy.id,
            version="1.0.0",
            code_hash="a" * 64,
            configuration_version="cfg-1",
        )
        session.add_all([instrument, version])
        await session.flush()
        session.add(
            VenueInstrument(
                venue_id=venue.id,
                instrument_id=instrument.id,
                symbol="BTC-USD",
            )
        )
        await session.commit()


def valid_payload(signal_id: uuid.UUID | None = None) -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "schema_version": "1.0",
        "signal_id": str(signal_id or uuid.uuid4()),
        "strategy_id": "olc",
        "strategy_version": "1.0.0",
        "configuration_version": "cfg-1",
        "environment": "development",
        "timestamp": now.isoformat(),
        "expiry": (now + timedelta(minutes=5)).isoformat(),
        "venue": "coinbase",
        "instrument": "btc-usd",
        "direction": "LONG",
        "entry_price": "65000.00",
        "reference_price": "65001.00",
        "stop": "64000.00",
        "targets": ["67000.00", "68000.00"],
        "expected_rr": "2.0",
        "timeframe": "15m",
        "setup_score": "82.5",
        "regime": "NORMAL",
        "metadata": {"atr": "500", "confidence": "0.75"},
    }


def gateway_headers(nonce: str = "test-nonce") -> dict[str, str]:
    return {
        "X-Olive-Key-Id": "test",
        "X-Olive-Timestamp": "1000",
        "X-Olive-Nonce": nonce,
        "X-Olive-Signature": "test",
    }


async def test_authenticated_signal_is_persisted_as_received(
    gateway_context: GatewayTestContext,
) -> None:
    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview",
        json=valid_payload(),
        headers=gateway_headers(),
    )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "RECEIVED"

    async with gateway_context.sessions() as session:
        record = await session.get(SignalIntakeRecord, uuid.UUID(response.json()["intake_id"]))
        assert record is not None
        assert record.strategy_version_id is not None
        assert record.venue_instrument_id is not None


async def test_duplicate_signal_id_is_rejected(gateway_context: GatewayTestContext) -> None:
    signal_id = uuid.uuid4()
    payload = valid_payload(signal_id)
    first = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=payload, headers=gateway_headers("n1")
    )
    second = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=payload, headers=gateway_headers("n2")
    )
    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["code"] == "DUPLICATE_SIGNAL"


async def test_unknown_instrument_rejection_is_persisted(
    gateway_context: GatewayTestContext,
) -> None:
    payload = valid_payload()
    payload["instrument"] = "UNKNOWN"
    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=payload, headers=gateway_headers()
    )
    assert response.status_code == 422
    assert response.json()["code"] == "UNKNOWN_INSTRUMENT"
    assert response.json()["intake_id"]

    async with gateway_context.sessions() as session:
        record = await session.get(SignalIntakeRecord, uuid.UUID(response.json()["intake_id"]))
        assert record is not None
        assert record.status == SignalIntakeStatus.REJECTED


async def test_malformed_json_rejection_is_persisted(
    gateway_context: GatewayTestContext,
) -> None:
    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview",
        content=b"{",
        headers={**gateway_headers(), "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "MALFORMED_JSON"
    assert response.json()["intake_id"]


async def test_authentication_happens_before_payload_processing(
    gateway_context: GatewayTestContext,
) -> None:
    app.dependency_overrides[get_signal_authenticator] = RejectAuthenticator
    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview",
        content=b"{",
        headers=gateway_headers(),
    )
    assert response.status_code == 401
    async with gateway_context.sessions() as session:
        count = await session.scalar(select(func.count()).select_from(SignalIntakeRecord))
        assert count == 0
