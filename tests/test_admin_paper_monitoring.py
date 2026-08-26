from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from olive.config import Settings, get_settings
from olive.db import Base, get_session
from olive.gateway.models import (
    SignalDirection,
    SignalEnvironment,
    SignalIntakeRecord,
    SignalIntakeStatus,
)
from olive.main import app
from olive.paper.models import PaperPipelineRunRecord
from olive.risk.models import TradeRiskDecisionRecord


@pytest.fixture
async def admin_client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    signal_id = uuid.uuid4()
    async with sessions() as session:
        intake = SignalIntakeRecord(
            signal_id=signal_id,
            status=SignalIntakeStatus.RISK_REVIEW,
            payload_hash="a" * 64,
            environment=SignalEnvironment.STAGING,
            direction=SignalDirection.LONG,
            entry_price=Decimal("65000"),
            stop_price=Decimal("64000"),
            targets=["67000", "68000"],
        )
        session.add(intake)
        await session.flush()
        session.add(
            TradeRiskDecisionRecord(
                signal_intake_id=intake.id,
                decision="APPROVED",
                requested_risk_pct=Decimal("1"),
                approved_risk_pct=Decimal("1"),
                position_size=Decimal("1"),
                base_risk_pct=Decimal("1"),
                equity_snapshot=Decimal("100000"),
                available_margin_snapshot=Decimal("50000"),
                multipliers={},
                limits={},
                reasons=[],
            )
        )
        session.add(
            PaperPipelineRunRecord(
                signal_id=signal_id,
                order_id=uuid.uuid4(),
                order_status="FILLED",
                protection_status="PROTECTED",
                reconciled=True,
                realized_pnl=Decimal("125.50"),
            )
        )
        await session.commit()

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        admin_api_key=SecretStr("test-admin-key-that-is-at-least-32-characters")
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        await engine.dispose()


async def test_admin_lists_paper_execution_with_summary(admin_client: AsyncClient) -> None:
    response = await admin_client.get(
        "/api/v1/admin/paper-executions",
        headers={"Authorization": "Bearer test-admin-key-that-is-at-least-32-characters"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "total_executions": 1,
        "filled_executions": 1,
        "protected_executions": 1,
        "reconciled_executions": 1,
        "total_realized_pnl": "125.500000000000",
        "latest_execution_at": body["summary"]["latest_execution_at"],
    }
    assert body["executions"][0]["risk_decision"] == "APPROVED"
    assert body["executions"][0]["order_status"] == "FILLED"
    assert body["executions"][0]["protection_status"] == "PROTECTED"


async def test_admin_execution_limit_is_bounded(admin_client: AsyncClient) -> None:
    response = await admin_client.get(
        "/api/v1/admin/paper-executions?limit=201",
        headers={"Authorization": "Bearer test-admin-key-that-is-at-least-32-characters"},
    )
    assert response.status_code == 422


async def test_admin_endpoint_requires_bearer_token(admin_client: AsyncClient) -> None:
    missing = await admin_client.get("/api/v1/admin/paper-executions")
    invalid = await admin_client.get(
        "/api/v1/admin/paper-executions",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert missing.status_code == 401
    assert invalid.status_code == 401
