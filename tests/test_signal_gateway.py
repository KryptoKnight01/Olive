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
from olive.config import AppEnvironment, Settings
from olive.db import Base, get_session
from olive.domain.models import (
    Asset,
    AssetClass,
    Instrument,
    InstrumentType,
    RecordStatus,
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
from olive.paper.models import PaperPipelineRunRecord
from olive.paper.orchestration import AutomaticPaperOrchestrator
from olive.risk.models import SingleTradeRiskPolicyRecord
from olive.validation.models import SignalValidationPolicy


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
        session.add(
            SignalValidationPolicy(
                strategy_version_id=version.id,
                allowed_timeframes=["15m"],
                max_entry_deviation_pct=Decimal("1.0"),
                min_expected_rr=Decimal("1.5"),
                min_setup_score=Decimal("70"),
            )
        )
        session.add(
            SingleTradeRiskPolicyRecord(
                strategy_version_id=version.id,
                base_risk_pct=Decimal("1"),
                max_risk_pct=Decimal("1.5"),
                max_notional=Decimal("100000"),
                max_leverage=Decimal("3"),
                max_margin=Decimal("50000"),
                min_stop_distance_pct=Decimal("0.25"),
                max_stop_distance_pct=Decimal("10"),
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
    assert response.json()["status"] == "RISK_REVIEW"

    async with gateway_context.sessions() as session:
        record = await session.get(SignalIntakeRecord, uuid.UUID(response.json()["intake_id"]))
        assert record is not None
        assert record.strategy_version_id is not None
        assert record.venue_instrument_id is not None


async def test_validated_signal_can_automatically_execute_in_paper(
    gateway_context: GatewayTestContext,
) -> None:
    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview",
        json=valid_payload(),
        headers=gateway_headers("paper-auto"),
    )
    intake_id = uuid.UUID(response.json()["intake_id"])
    settings = Settings(
        app_env=AppEnvironment.STAGING,
        paper_auto_execute=True,
        paper_equity=Decimal("100000"),
        paper_available_margin=Decimal("50000"),
        paper_requested_risk_pct=Decimal("1"),
    )
    async with gateway_context.sessions() as session:
        result = await AutomaticPaperOrchestrator(session, settings).execute(intake_id)
        assert result.outcome == "EXECUTED"
        assert result.order_status == "FILLED"
        assert result.protection_status == "PROTECTED"
        assert result.reconciled is True
        run = await session.scalar(
            select(PaperPipelineRunRecord).where(
                PaperPipelineRunRecord.signal_id == uuid.UUID(response.json()["signal_id"])
            )
        )
        assert run is not None


def test_signal_environment_uses_wire_values_in_database() -> None:
    environment_type = SignalIntakeRecord.__table__.c.environment.type
    assert environment_type.enums == [
        "development",
        "testing",
        "paper",
        "staging",
        "production",
    ]


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


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"entry_price": "66000.00"}, "ENTRY_DEVIATION_EXCEEDED"),
        ({"stop": "66000.00"}, "INVALID_STOP_TARGET_LOGIC"),
        ({"targets": ["64000.00"]}, "INVALID_STOP_TARGET_LOGIC"),
        ({"expected_rr": "1.0"}, "MINIMUM_RR_NOT_MET"),
        ({"setup_score": "60"}, "MINIMUM_SETUP_SCORE_NOT_MET"),
        ({"timeframe": "1m"}, "TIMEFRAME_NOT_ALLOWED"),
    ],
)
async def test_phase3_validation_rejections_are_persisted(
    gateway_context: GatewayTestContext,
    changes: dict[str, object],
    expected_code: str,
) -> None:
    payload = valid_payload()
    payload.update(changes)
    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=payload, headers=gateway_headers()
    )
    assert response.status_code == 422
    assert response.json()["code"] == expected_code

    async with gateway_context.sessions() as session:
        record = await session.get(SignalIntakeRecord, uuid.UUID(response.json()["intake_id"]))
        assert record is not None
        assert record.status == SignalIntakeStatus.REJECTED
        assert record.validation_details is not None
        assert record.validation_details["rule"] == expected_code
        assert record.validated_at is not None


async def test_phase3_direction_policy_is_enforced(
    gateway_context: GatewayTestContext,
) -> None:
    async with gateway_context.sessions() as session:
        policy = await session.scalar(select(SignalValidationPolicy))
        assert policy is not None
        policy.allowed_directions = ["SHORT"]
        await session.commit()

    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=valid_payload(), headers=gateway_headers()
    )
    assert response.status_code == 422
    assert response.json()["code"] == "DIRECTION_NOT_ALLOWED"


async def test_phase3_session_policy_is_enforced(
    gateway_context: GatewayTestContext,
) -> None:
    async with gateway_context.sessions() as session:
        policy = await session.scalar(select(SignalValidationPolicy))
        assert policy is not None
        policy.allowed_weekdays = []
        await session.commit()

    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=valid_payload(), headers=gateway_headers()
    )
    assert response.status_code == 422
    assert response.json()["code"] == "SESSION_CLOSED"


async def test_phase3_disabled_strategy_is_rejected(
    gateway_context: GatewayTestContext,
) -> None:
    async with gateway_context.sessions() as session:
        strategy = await session.scalar(select(Strategy))
        assert strategy is not None
        strategy.status = RecordStatus.SUSPENDED
        await session.commit()

    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=valid_payload(), headers=gateway_headers()
    )
    assert response.status_code == 422
    assert response.json()["code"] == "STRATEGY_DISABLED"


async def test_phase3_disabled_instrument_is_rejected(
    gateway_context: GatewayTestContext,
) -> None:
    async with gateway_context.sessions() as session:
        instrument = await session.scalar(select(Instrument))
        assert instrument is not None
        instrument.status = RecordStatus.SUSPENDED
        await session.commit()

    response = await gateway_context.client.post(
        "/api/v1/signals/tradingview", json=valid_payload(), headers=gateway_headers()
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INSTRUMENT_DISABLED"


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
