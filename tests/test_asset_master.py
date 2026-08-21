from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from olive.db import Base, get_session
from olive.main import app


@pytest.fixture
async def asset_client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()


async def create_asset(
    client: AsyncClient, code: str, name: str, asset_class: str, currency: str | None = None
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/asset-master/assets",
        json={
            "code": code,
            "name": name,
            "asset_class": asset_class,
            "currency_code": currency,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_canonical_venue_symbol_resolution(asset_client: AsyncClient) -> None:
    btc = await create_asset(asset_client, "btc", "Bitcoin", "CRYPTO")
    usd = await create_asset(asset_client, "usd", "US Dollar", "CASH", "usd")

    underlying_response = await asset_client.post(
        "/api/v1/asset-master/underlyings",
        json={
            "code": "btc",
            "name": "Bitcoin economic exposure",
            "primary_asset_id": btc["id"],
            "asset_class": "CRYPTO",
            "themes": ["crypto-beta"],
        },
    )
    assert underlying_response.status_code == 201
    underlying = underlying_response.json()

    instrument_response = await asset_client.post(
        "/api/v1/asset-master/instruments",
        json={
            "code": "btc-usd-spot",
            "name": "Bitcoin / US Dollar Spot",
            "underlying_id": underlying["id"],
            "base_asset_id": btc["id"],
            "quote_asset_id": usd["id"],
            "settlement_asset_id": usd["id"],
            "instrument_type": "SPOT",
            "tick_size": "0.01",
            "lot_size": "0.00000001",
            "contract_multiplier": "1",
            "shortable": False,
        },
    )
    assert instrument_response.status_code == 201, instrument_response.text
    instrument = instrument_response.json()

    venue_response = await asset_client.post(
        "/api/v1/asset-master/venues",
        json={"code": "coinbase", "name": "Coinbase", "country_code": "us"},
    )
    assert venue_response.status_code == 201
    venue = venue_response.json()

    mapping_response = await asset_client.post(
        "/api/v1/asset-master/venue-instruments",
        json={
            "venue_id": venue["id"],
            "instrument_id": instrument["id"],
            "symbol": "btc-usd",
        },
    )
    assert mapping_response.status_code == 201

    resolved_response = await asset_client.get(
        "/api/v1/asset-master/resolve",
        params={"venue_code": "coinbase", "symbol": "btc-usd"},
    )
    assert resolved_response.status_code == 200
    resolved = resolved_response.json()
    assert resolved["instrument_code"] == "BTC-USD-SPOT"
    assert resolved["underlying_code"] == "BTC"
    assert resolved["venue_symbol"] == "BTC-USD"


async def test_duplicate_asset_code_is_rejected(asset_client: AsyncClient) -> None:
    await create_asset(asset_client, "BTC", "Bitcoin", "CRYPTO")
    response = await asset_client.post(
        "/api/v1/asset-master/assets",
        json={"code": "btc", "name": "Duplicate", "asset_class": "CRYPTO"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


async def test_underlying_asset_class_must_match_primary_asset(
    asset_client: AsyncClient,
) -> None:
    btc = await create_asset(asset_client, "BTC", "Bitcoin", "CRYPTO")
    response = await asset_client.post(
        "/api/v1/asset-master/underlyings",
        json={
            "code": "BTC",
            "name": "Bitcoin",
            "primary_asset_id": btc["id"],
            "asset_class": "EQUITY",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_unknown_venue_symbol_fails_closed(asset_client: AsyncClient) -> None:
    response = await asset_client.get(
        "/api/v1/asset-master/resolve",
        params={"venue_code": "UNKNOWN", "symbol": "UNKNOWN"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
