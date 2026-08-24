from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select

from olive.config import get_settings
from olive.db import create_database_engine, create_session_factory
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
from olive.gateway.models import SignalIntakeRecord, SignalIntakeStatus
from olive.risk.models import (
    HierarchicalExposureLimitRecord,
    PortfolioRiskDecisionRecord,
    PortfolioRiskPolicyRecord,
    SingleTradeRiskPolicyRecord,
    TradeRiskDecisionRecord,
)
from olive.risk.schemas import (
    HierarchicalRiskInput,
    PortfolioRiskInput,
    PositionSide,
    RiskDecisionOutcome,
)
from olive.risk.service import (
    HierarchicalRiskService,
    PortfolioRiskService,
    SingleTradeRiskService,
)
from olive.validation.models import SignalValidationPolicy


async def seed() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            if await session.scalar(select(Asset).where(Asset.code == "BTC")) is not None:
                print("Phase 2 smoke reference data already exists.")
                return

            btc = Asset(code="BTC", name="Bitcoin", asset_class=AssetClass.CRYPTO)
            usd = Asset(
                code="USD",
                name="US Dollar",
                asset_class=AssetClass.CASH,
                currency_code="USD",
            )
            session.add_all([btc, usd])
            await session.flush()

            underlying = Underlying(
                code="BTC",
                name="Bitcoin economic exposure",
                primary_asset_id=btc.id,
                asset_class=AssetClass.CRYPTO,
                themes=["crypto-beta"],
            )
            venue = Venue(code="COINBASE", name="Coinbase", country_code="US")
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
                code_hash="0" * 64,
                configuration_version="smoke-1",
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
            session.add(
                PortfolioRiskPolicyRecord(
                    scope_key="default",
                    max_gross_exposure_pct=Decimal("300"),
                    max_net_exposure_pct=Decimal("200"),
                    max_long_exposure_pct=Decimal("250"),
                    max_short_exposure_pct=Decimal("150"),
                    max_open_stop_risk_pct=Decimal("5"),
                    max_margin_utilization_pct=Decimal("80"),
                    max_leverage=Decimal("3"),
                    max_concurrent_positions=10,
                )
            )
            session.add(
                HierarchicalExposureLimitRecord(
                    configuration_version="smoke-1",
                    dimension="UNDERLYING",
                    scope_key="BTC",
                    metric="GROSS_NOTIONAL",
                    maximum=Decimal("100000"),
                    enabled=True,
                )
            )
            await session.commit()
            print("Seeded Phase 2 smoke reference data.")
    finally:
        await engine.dispose()


def make_payload() -> bytes:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "signal_id": str(uuid.uuid4()),
        "strategy_id": "OLC",
        "strategy_version": "1.0.0",
        "configuration_version": "smoke-1",
        "environment": "development",
        "timestamp": now.isoformat(),
        "expiry": (now + timedelta(minutes=5)).isoformat(),
        "venue": "COINBASE",
        "instrument": "BTC-USD",
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
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def signed_headers(body: bytes, nonce: str) -> dict[str, str]:
    settings = get_settings()
    secret = settings.signal_hmac_secret
    if secret is None or not secret.get_secret_value():
        raise RuntimeError("OLIVE_SIGNAL_HMAC_SECRET must be configured for the smoke test")
    timestamp = str(int(datetime.now(UTC).timestamp()))
    message = timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body
    signature = hmac.new(secret.get_secret_value().encode(), message, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Olive-Key-Id": settings.signal_hmac_key_id,
        "X-Olive-Timestamp": timestamp,
        "X-Olive-Nonce": nonce,
        "X-Olive-Signature": f"sha256={signature}",
    }


def post(url: str, body: bytes, headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def send(url: str) -> None:
    body = make_payload()
    nonce = f"smoke-{uuid.uuid4()}"
    headers = signed_headers(body, nonce)

    accepted_status, accepted = post(url, body, headers)
    if accepted_status != 202 or accepted.get("status") != "RISK_REVIEW":
        raise RuntimeError(f"signed signal was not received: {accepted_status} {accepted}")
    print(f"PASS signed signal received: intake_id={accepted['intake_id']}")

    replay_status, replay = post(url, body, headers)
    if replay_status != 409 or replay.get("code") != "REPLAY_DETECTED":
        raise RuntimeError(f"nonce replay was not rejected: {replay_status} {replay}")
    print("PASS identical nonce replay rejected")

    duplicate_headers = signed_headers(body, f"smoke-{uuid.uuid4()}")
    duplicate_status, duplicate = post(url, body, duplicate_headers)
    if duplicate_status != 409 or duplicate.get("code") != "DUPLICATE_SIGNAL":
        raise RuntimeError(f"duplicate signal ID was not rejected: {duplicate_status} {duplicate}")
    print("PASS duplicate signal ID rejected with a fresh nonce")

    invalid_payload = json.loads(body)
    invalid_payload["signal_id"] = str(uuid.uuid4())
    invalid_payload["stop"] = "66000.00"
    invalid_body = json.dumps(invalid_payload, separators=(",", ":"), sort_keys=True).encode()
    invalid_headers = signed_headers(invalid_body, f"smoke-{uuid.uuid4()}")
    invalid_status, invalid = post(url, invalid_body, invalid_headers)
    if invalid_status != 422 or invalid.get("code") != "INVALID_STOP_TARGET_LOGIC":
        raise RuntimeError(f"invalid Phase 3 signal was not rejected: {invalid_status} {invalid}")
    print("PASS Phase 3 stop/target validation rejected an illogical signal")


async def risk() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            intake = await session.scalar(
                select(SignalIntakeRecord)
                .where(SignalIntakeRecord.status == SignalIntakeStatus.RISK_REVIEW)
                .order_by(desc(SignalIntakeRecord.created_at))
            )
            if intake is None:
                raise RuntimeError("no validated signal is available for risk review")
            decision = await SingleTradeRiskService(session).evaluate(
                intake.id,
                equity=Decimal("100000"),
                available_margin=Decimal("50000"),
                requested_risk_pct=Decimal("1"),
            )
            if decision.outcome is not RiskDecisionOutcome.APPROVED:
                raise RuntimeError(f"unexpected Phase 4 decision: {decision.decision}")
            print(f"PASS Phase 4 stop-based risk decision: size={decision.position_size}")
    finally:
        await engine.dispose()


async def portfolio() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            trade_decision = await session.scalar(
                select(TradeRiskDecisionRecord).order_by(
                    desc(TradeRiskDecisionRecord.created_at)
                )
            )
            if trade_decision is None:
                raise RuntimeError("no Phase 4 trade decision is available")
            decision = await PortfolioRiskService(session).evaluate(
                trade_decision.id,
                PortfolioRiskInput(
                    signal_id=uuid.uuid4(),
                    equity=trade_decision.equity_snapshot,
                    proposed_side=PositionSide.LONG,
                    proposed_notional=Decimal("65000"),
                    proposed_stop_risk=Decimal("1000"),
                    proposed_margin=Decimal("21666.67"),
                ),
            )
            if decision.outcome is not RiskDecisionOutcome.APPROVED:
                raise RuntimeError(f"unexpected Phase 5 decision: {decision.decision}")
            print(
                "PASS Phase 5 projected portfolio decision: "
                f"notional={decision.approved_notional}"
            )
    finally:
        await engine.dispose()


async def hierarchy() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            portfolio_decision = await session.scalar(
                select(PortfolioRiskDecisionRecord).order_by(
                    desc(PortfolioRiskDecisionRecord.created_at)
                )
            )
            if portfolio_decision is None:
                raise RuntimeError("no Phase 5 portfolio decision is available")
            decision = await HierarchicalRiskService(session).evaluate(
                portfolio_decision.id,
                HierarchicalRiskInput.model_validate(
                    {
                        "signal_id": uuid.uuid4(),
                        "proposed_tags": {"UNDERLYING": ["BTC"]},
                        "proposed_notional": "65000",
                        "proposed_stop_risk": "1000",
                        "proposed_margin": "21666.67",
                    }
                ),
                configuration_version="smoke-1",
            )
            if decision.outcome is not RiskDecisionOutcome.APPROVED:
                raise RuntimeError(f"unexpected Phase 6 decision: {decision.decision}")
            print(f"PASS Phase 6 hierarchical limit decision: {decision.decision}")
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Olive Phase 2 live smoke test")
    parser.add_argument(
        "command", choices=("seed", "send", "risk", "portfolio", "hierarchy")
    )
    parser.add_argument(
        "--url",
        default="http://api:8000/api/v1/signals/tradingview",
        help="TradingView webhook URL used by the send command",
    )
    args = parser.parse_args()
    try:
        if args.command == "seed":
            asyncio.run(seed())
        elif args.command == "risk":
            asyncio.run(risk())
        elif args.command == "portfolio":
            asyncio.run(portfolio())
        elif args.command == "hierarchy":
            asyncio.run(hierarchy())
        else:
            send(args.url)
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
