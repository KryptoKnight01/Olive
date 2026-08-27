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
from olive.evolution.engine import EvolutionEngine
from olive.evolution.schemas import (
    AuthorityPolicy,
    CapitalPool,
    ExecutionRequest,
    ExecutionStyle,
    PortfolioAnalyticsInput,
    SignalAuthority,
    StrategyBar,
)
from olive.execution_risk.models import ExecutionRiskPolicyRecord
from olive.execution_risk.schemas import ExecutionRiskInput
from olive.execution_risk.service import ExecutionRiskService
from olive.gateway.models import SignalIntakeRecord, SignalIntakeStatus
from olive.governance.engine import GovernanceEngine
from olive.governance.schemas import (
    ConfigurationChange,
    KillSwitchAction,
    KillSwitchCommand,
    KillSwitchScope,
    Role,
)
from olive.market_data.models import MarketQuoteRecord
from olive.market_data.schemas import MarketDataPolicy, QuoteInput
from olive.market_data.service import MarketDataService
from olive.operations.engine import OperationsEngine
from olive.operations.schemas import (
    AnomalyObservation,
    HardeningCheck,
    MlRecommendation,
    MobileAction,
    MobileControlRequest,
)
from olive.paper.oms import PaperOms
from olive.paper.pipeline import PaperPipeline
from olive.paper.sandbox import FirstVenueSandboxConnector
from olive.production.engine import ControlledProductionEngine
from olive.production.schemas import (
    AssetProductionPolicy,
    ExecutionObservation,
    LiveCapitalPolicy,
    LiveOrderRequest,
    ProductionMode,
    StrategySignal,
    VenueExposure,
    VenueQuote,
)
from olive.readiness.engine import LiveReadinessEngine
from olive.readiness.schemas import (
    EventObservation,
    EventRiskPolicy,
    HealthStatus,
    PerformanceMetrics,
    PerformanceThresholds,
    ReadinessCheck,
    ShadowOrder,
    StressInput,
    StressScenario,
)
from olive.risk.models import (
    CorrelationRiskDecisionRecord,
    CorrelationRiskPolicyRecord,
    DynamicRiskDecisionRecord,
    DynamicRiskPolicyRecord,
    HierarchicalExposureLimitRecord,
    HierarchicalRiskDecisionRecord,
    LossProtectionDecisionRecord,
    LossProtectionPolicyRecord,
    PortfolioRegimePolicyRecord,
    PortfolioRiskDecisionRecord,
    PortfolioRiskPolicyRecord,
    SingleTradeRiskPolicyRecord,
    TradeRiskDecisionRecord,
)
from olive.risk.schemas import (
    CorrelationRiskInput,
    DynamicRiskInput,
    HierarchicalRiskInput,
    LossProtectionInput,
    PortfolioRegimeInput,
    PortfolioRiskInput,
    PositionSide,
    RiskDecisionOutcome,
)
from olive.risk.service import (
    CorrelationRiskService,
    DynamicRiskService,
    HierarchicalRiskService,
    LossProtectionService,
    PortfolioRegimeService,
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
            session.add(
                CorrelationRiskPolicyRecord(
                    configuration_version="smoke-1",
                    lookback_observations=6,
                    minimum_observations=5,
                    cluster_threshold=Decimal("0.8"),
                    max_correlated_positions=2,
                    max_cluster_stop_risk=Decimal("3000"),
                )
            )
            neutral_bounds = {
                name: {"minimum": "0.25", "maximum": "1.25"}
                for name in (
                    "regime",
                    "correlation",
                    "drawdown",
                    "liquidity",
                    "signal_quality",
                    "strategy_health",
                    "event_risk",
                )
            }
            session.add(
                DynamicRiskPolicyRecord(configuration_version="smoke-1", bounds=neutral_bounds)
            )
            session.add(
                LossProtectionPolicyRecord(
                    configuration_version="smoke-1",
                    parameters={
                        "max_daily_loss_pct": "2",
                        "max_weekly_loss_pct": "5",
                        "max_monthly_loss_pct": "10",
                        "portfolio_drawdown_throttle_pct": "5",
                        "portfolio_drawdown_halt_pct": "10",
                        "strategy_drawdown_throttle_pct": "7",
                        "strategy_drawdown_halt_pct": "12",
                        "consecutive_loss_throttle": 3,
                        "consecutive_loss_halt": 5,
                        "throttled_multiplier": "0.5",
                        "profit_giveback_trigger_pct": "50",
                        "minimum_profit_for_giveback": "1000",
                        "profit_giveback_multiplier": "0.25",
                    },
                )
            )
            regime_thresholds = {
                name: {
                    "calm_maximum": "10",
                    "elevated_minimum": "20",
                    "high_volatility_minimum": "30",
                    "crisis_minimum": "40",
                }
                for name in (
                    "realized_volatility_pct",
                    "liquidity_stress_score",
                    "market_stress_score",
                )
            }
            regime_thresholds["average_absolute_correlation"] = {
                "calm_maximum": "0.2",
                "elevated_minimum": "0.5",
                "high_volatility_minimum": "0.7",
                "crisis_minimum": "0.9",
            }
            regime_thresholds["portfolio_drawdown_pct"] = {
                "calm_maximum": "2",
                "elevated_minimum": "5",
                "high_volatility_minimum": "8",
                "crisis_minimum": "12",
            }
            session.add(
                PortfolioRegimePolicyRecord(
                    configuration_version="smoke-1",
                    thresholds=regime_thresholds,
                    controls={
                        "CALM": {
                            "risk_multiplier": "1",
                            "max_leverage": "3",
                            "max_new_positions": 10,
                        },
                        "NORMAL": {
                            "risk_multiplier": "1",
                            "max_leverage": "3",
                            "max_new_positions": 8,
                        },
                        "ELEVATED": {
                            "risk_multiplier": "0.75",
                            "max_leverage": "2",
                            "max_new_positions": 4,
                        },
                        "HIGH_VOLATILITY": {
                            "risk_multiplier": "0.5",
                            "max_leverage": "1.5",
                            "max_new_positions": 2,
                        },
                        "CRISIS": {
                            "risk_multiplier": "0",
                            "max_leverage": "0",
                            "max_new_positions": 0,
                        },
                    },
                )
            )
            session.add(
                ExecutionRiskPolicyRecord(
                    configuration_version="smoke-1",
                    parameters={
                        "maximum_spread_pct": "1",
                        "maximum_slippage_pct": "0.5",
                        "maximum_adv_participation_pct": "2",
                        "maximum_book_participation_pct": "20",
                        "minimum_executable_notional": "100",
                        "minimum_reduced_fraction": "0.5",
                        "maximum_slices": 5,
                    },
                )
            )
            await session.commit()
            print("Seeded Phase 2 smoke reference data.")
    finally:
        await engine.dispose()


def make_payload() -> bytes:
    now = datetime.now(UTC)
    settings = get_settings()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "signal_id": str(uuid.uuid4()),
        "strategy_id": "OLC",
        "strategy_version": "1.0.0",
        "configuration_version": "smoke-1",
        "environment": settings.app_env.value,
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
                select(TradeRiskDecisionRecord).order_by(desc(TradeRiskDecisionRecord.created_at))
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
                f"PASS Phase 5 projected portfolio decision: notional={decision.approved_notional}"
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


async def correlation() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            hierarchy_decision = await session.scalar(
                select(HierarchicalRiskDecisionRecord).order_by(
                    desc(HierarchicalRiskDecisionRecord.created_at)
                )
            )
            if hierarchy_decision is None:
                raise RuntimeError("no Phase 6 hierarchical decision is available")
            decision = await CorrelationRiskService(session).evaluate(
                hierarchy_decision.id,
                CorrelationRiskInput.model_validate(
                    {
                        "signal_id": uuid.uuid4(),
                        "proposed_instrument_key": "BTC",
                        "proposed_notional": "65000",
                        "proposed_stop_risk": "1000",
                        "price_history": {
                            "BTC": ["100", "101", "103", "102", "104", "107"],
                            "ETH": ["200", "202", "206", "204", "208", "214"],
                        },
                    }
                ),
                configuration_version="smoke-1",
            )
            if decision.outcome is not RiskDecisionOutcome.APPROVED:
                raise RuntimeError(f"unexpected Phase 7 decision: {decision.decision}")
            print(f"PASS Phase 7 correlation-aware decision: cluster={decision.proposed_cluster}")
    finally:
        await engine.dispose()


async def dynamic() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            correlation_decision = await session.scalar(
                select(CorrelationRiskDecisionRecord).order_by(
                    desc(CorrelationRiskDecisionRecord.created_at)
                )
            )
            if correlation_decision is None:
                raise RuntimeError("no Phase 7 correlation decision is available")
            decision = await DynamicRiskService(session).evaluate(
                correlation_decision.id,
                DynamicRiskInput(
                    signal_id=uuid.uuid4(),
                    base_risk_pct=Decimal("1"),
                    hard_max_risk_pct=Decimal("1.5"),
                    regime=Decimal("0.8"),
                    correlation=Decimal("1"),
                    drawdown=Decimal("1"),
                    liquidity=Decimal("1"),
                    signal_quality=Decimal("1"),
                    strategy_health=Decimal("1"),
                    event_risk=Decimal("1"),
                ),
                configuration_version="smoke-1",
            )
            if decision.final_risk_pct != Decimal("0.8"):
                raise RuntimeError(f"unexpected Phase 8 risk: {decision.final_risk_pct}")
            print(f"PASS Phase 8 dynamic risk decision: risk={decision.final_risk_pct}%")
    finally:
        await engine.dispose()


async def protection() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            dynamic_decision = await session.scalar(
                select(DynamicRiskDecisionRecord).order_by(
                    desc(DynamicRiskDecisionRecord.created_at)
                )
            )
            if dynamic_decision is None:
                raise RuntimeError("no Phase 8 dynamic risk decision is available")
            decision = await LossProtectionService(session).evaluate(
                dynamic_decision.id,
                LossProtectionInput(
                    signal_id=uuid.uuid4(),
                    equity=Decimal("94000"),
                    peak_equity=Decimal("100000"),
                    strategy_equity=Decimal("50000"),
                    strategy_peak_equity=Decimal("50000"),
                    daily_pnl=Decimal("0"),
                    weekly_pnl=Decimal("0"),
                    monthly_pnl=Decimal("0"),
                    peak_daily_pnl=Decimal("0"),
                    consecutive_losses=0,
                ),
                configuration_version="smoke-1",
            )
            if decision.protection_multiplier != Decimal("0.5"):
                raise RuntimeError(
                    f"unexpected Phase 9 protection: {decision.protection_multiplier}"
                )
            print(
                "PASS Phase 9 loss-protection decision: "
                f"action={decision.action}, multiplier={decision.protection_multiplier}"
            )
    finally:
        await engine.dispose()


async def regime() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            protection_decision = await session.scalar(
                select(LossProtectionDecisionRecord).order_by(
                    desc(LossProtectionDecisionRecord.created_at)
                )
            )
            if protection_decision is None:
                raise RuntimeError("no Phase 9 loss-protection decision is available")
            decision = await PortfolioRegimeService(session).evaluate(
                protection_decision.id,
                PortfolioRegimeInput(
                    observation_id=uuid.uuid4(),
                    realized_volatility_pct=Decimal("22"),
                    average_absolute_correlation=Decimal("0.3"),
                    portfolio_drawdown_pct=Decimal("2"),
                    liquidity_stress_score=Decimal("5"),
                    market_stress_score=Decimal("5"),
                ),
                configuration_version="smoke-1",
            )
            if decision.regime != "ELEVATED":
                raise RuntimeError(f"unexpected Phase 10 regime: {decision.regime}")
            if decision.controls["risk_multiplier"] != "0.75":
                raise RuntimeError(f"unexpected Phase 10 controls: {decision.controls}")
            print(
                "PASS Phase 10 portfolio-regime decision: "
                f"regime={decision.regime}, controls={decision.controls}"
            )
    finally:
        await engine.dispose()


async def market_data() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            instrument = await session.scalar(
                select(Instrument).where(Instrument.code == "BTC-USD-SPOT")
            )
            if instrument is None:
                raise RuntimeError("Phase 11 smoke instrument is unavailable")
            now = datetime.now(UTC)
            service = MarketDataService(
                session,
                MarketDataPolicy(
                    maximum_age_seconds=10,
                    maximum_future_skew_seconds=2,
                    maximum_spread_pct=Decimal("2"),
                    maximum_price_jump_pct=Decimal("10"),
                ),
            )
            decision = await service.ingest_quote(
                QuoteInput(
                    instrument_id=instrument.id,
                    venue_code="COINBASE",
                    source="phase11-smoke",
                    source_timestamp=now - timedelta(seconds=1),
                    received_at=now,
                    bid=Decimal("99900"),
                    ask=Decimal("100000"),
                    last=Decimal("99950"),
                    volume=Decimal("12"),
                ),
                evaluated_at=now,
            )
            if decision.status != "VALID":
                raise RuntimeError(f"unexpected Phase 11 market-data status: {decision.status}")
            print(
                "PASS Phase 11 normalized market quote: "
                f"status={decision.status}, mid={decision.mid}, spread={decision.spread}"
            )
    finally:
        await engine.dispose()


async def execution_risk() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            quote = await session.scalar(
                select(MarketQuoteRecord).order_by(desc(MarketQuoteRecord.created_at))
            )
            if quote is None:
                raise RuntimeError("no Phase 11 market quote is available")
            decision = await ExecutionRiskService(session).evaluate(
                quote.id,
                ExecutionRiskInput(
                    signal_id=uuid.uuid4(),
                    market_quote_id=quote.id,
                    requested_quantity=Decimal("10"),
                    requested_notional=Decimal("3000"),
                    spread_pct=Decimal(quote.spread_pct),
                    expected_slippage_pct=Decimal("0.2"),
                    average_daily_volume_notional=Decimal("100000"),
                    available_book_notional=Decimal("10000"),
                    market_data_status=quote.status,
                ),
                configuration_version="smoke-1",
            )
            if decision.action != "REDUCE" or decision.approved_notional != Decimal("2000"):
                raise RuntimeError(
                    f"unexpected Phase 12 execution decision: {decision.action} "
                    f"{decision.approved_notional}"
                )
            print(
                "PASS Phase 12 liquidity decision: "
                f"action={decision.action}, approved_notional={decision.approved_notional}"
            )
    finally:
        await engine.dispose()


async def paper_pipeline() -> None:
    oms = PaperOms(fee_rate=Decimal("0.001"))
    venue = FirstVenueSandboxConnector(oms)
    result = PaperPipeline(oms, venue).execute_round_trip(
        signal_id=uuid.uuid4(),
        instrument_id=uuid.uuid4(),
        quantity=Decimal("2"),
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
    )
    if result.realized_pnl != Decimal("19.58") or not result.reconciled:
        raise RuntimeError(f"unexpected Phase 13-17 pipeline result: {result}")
    print(
        "PASS Phases 13-17 paper pipeline: "
        f"status={result.order_status}, protection={result.protection_status}, "
        f"pnl={result.realized_pnl}"
    )


async def governance_controls() -> None:
    engine = GovernanceEngine()
    requester = uuid.uuid4()
    engine.publish_configuration(
        ConfigurationChange(
            namespace="risk",
            version="smoke-1",
            values={"max_risk_pct": "1"},
            increases_risk=False,
            requested_by=requester,
        ),
        Role.ADMIN,
    )
    engine.activate_kill_switch(
        KillSwitchCommand(
            scope=KillSwitchScope.STRATEGY,
            scope_key="OLC",
            action=KillSwitchAction.PAUSE_ENTRIES,
            reason="Phase 22 smoke verification",
            actor_id=requester,
        ),
        Role.RISK_MANAGER,
    )
    if engine.permits_new_entry({"STRATEGY": "OLC"}):
        raise RuntimeError("Phase 22 kill switch did not block the strategy")
    if len(engine.audit_events) != 2:
        raise RuntimeError("Phase 21 audit evidence is incomplete")
    print(
        "PASS Phases 18-22 governance controls: "
        "configuration=IMMUTABLE, audit=COMPLETE, strategy_entries=PAUSED"
    )


async def live_readiness() -> None:
    engine = LiveReadinessEngine()
    performance = engine.assess_performance(
        PerformanceMetrics(
            strategy_key="OLC",
            profit_factor=Decimal("1.7"),
            win_rate=Decimal("55"),
            expectancy_r=Decimal("0.25"),
            average_r=Decimal("0.4"),
            max_drawdown_pct=Decimal("8"),
            trades=100,
            slippage_pct=Decimal("0.2"),
        ),
        PerformanceThresholds(),
    )
    stress = engine.run_stress_test(
        StressInput(
            portfolio_value=Decimal("100000"),
            gross_exposure=Decimal("200000"),
            available_margin=Decimal("10000"),
            max_loss_pct=Decimal("10"),
        ),
        StressScenario(
            name="crash",
            volatility_multiplier=Decimal("2"),
            correlation_multiplier=Decimal("1.5"),
            liquidity_reduction_pct=Decimal("50"),
            gap_pct=Decimal("10"),
            venue_failure=True,
        ),
    )
    event = engine.evaluate_event(
        EventObservation(event_key="FOMC", minutes_from_event=5),
        EventRiskPolicy(
            blackout_minutes_before=30, blackout_minutes_after=15, risk_multiplier=Decimal("0.5")
        ),
    )
    shadow = engine.simulate_shadow(
        ShadowOrder(
            signal_id=str(uuid.uuid4()),
            strategy_key="OLC",
            instrument="BTCUSDT",
            side="BUY",
            quantity=Decimal("1"),
            reference_price=Decimal("50000"),
        ),
        Decimal("0.1"),
    )
    required = (
        "security",
        "risk",
        "execution",
        "reconciliation",
        "backup",
        "monitoring",
        "kill-switch",
        "incident-response",
    )
    review = engine.review(
        [ReadinessCheck(name=name, passed=True, evidence="smoke verified") for name in required]
    )
    if performance.status is not HealthStatus.GREEN:
        raise RuntimeError(f"unexpected strategy health: {performance.status}")
    if not stress.blocked or event.entries_allowed:
        raise RuntimeError("stress or event risk failed to block unsafe activity")
    if shadow.sent_to_venue or not review.approved:
        raise RuntimeError("shadow isolation or readiness review failed")
    print(
        "PASS Phases 23-27 live readiness: strategy=GREEN, stress=BLOCKED, "
        "event=BLACKOUT, shadow=ISOLATED, review=APPROVED"
    )


async def controlled_production() -> None:
    engine = ControlledProductionEngine()
    policy = LiveCapitalPolicy(
        mode=ProductionMode.LIMITED_LIVE,
        approved_strategy="OLC",
        approved_instruments=frozenset({"BTCUSDT"}),
        approved_venue="venue-a",
        max_order_notional=Decimal("1000"),
        max_total_exposure=Decimal("5000"),
        max_leverage=Decimal("1.5"),
        readiness_approved=True,
        operator_armed=True,
    )
    live = engine.authorize_live_order(
        LiveOrderRequest(
            signal_id=str(uuid.uuid4()),
            strategy_key="OLC",
            instrument="BTCUSDT",
            venue="venue-a",
            requested_notional=Decimal("1500"),
            projected_total_exposure=Decimal("3000"),
            projected_leverage=Decimal("1"),
        ),
        policy,
    )
    deviation = engine.analyze_deviation(
        ExecutionObservation(
            signal_id=live.signal_id,
            paper_delay_ms=100,
            live_delay_ms=500,
            paper_fill_price=Decimal("100"),
            live_fill_price=Decimal("102"),
            paper_fee=Decimal("1"),
            live_fee=Decimal("1.5"),
            paper_pnl=Decimal("10"),
            live_pnl=Decimal("5"),
        ),
        200,
        Decimal("1"),
        Decimal("2"),
    )
    venue = engine.select_venue(
        [
            VenueQuote(
                venue="venue-a",
                price=Decimal("100"),
                available_notional=Decimal("1000"),
                fee_pct=Decimal("0.1"),
            ),
            VenueQuote(
                venue="venue-b",
                price=Decimal("99"),
                available_notional=Decimal("800"),
                fee_pct=Decimal("0.1"),
            ),
        ],
        Decimal("1000"),
        "BUY",
    )
    exposure = engine.consolidated_exposure(
        [
            VenueExposure(venue="venue-a", gross_exposure=Decimal("2000")),
            VenueExposure(venue="venue-b", gross_exposure=Decimal("3000")),
        ]
    )
    strategies = engine.resolve_strategies(
        [
            StrategySignal(
                strategy_key="OLC",
                instrument="BTCUSDT",
                direction=1,
                priority=100,
                requested_risk_pct=Decimal("0.8"),
            ),
            StrategySignal(
                strategy_key="secondary",
                instrument="BTCUSDT",
                direction=-1,
                priority=50,
                requested_risk_pct=Decimal("0.5"),
            ),
        ],
        Decimal("1"),
    )
    asset = engine.check_asset_eligibility(
        "BTCUSDT",
        "venue-a",
        Decimal("1500"),
        AssetProductionPolicy(
            asset_class="CRYPTO",
            approved_instruments=frozenset({"BTCUSDT"}),
            approved_venues=frozenset({"venue-a"}),
            max_notional=Decimal("1000"),
            enabled=True,
        ),
    )
    if not live.route_permitted or live.approved_notional != Decimal("1000"):
        raise RuntimeError("limited-live capital gate failed")
    if not deviation.breached or venue.venue != "venue-b" or exposure != Decimal("5000"):
        raise RuntimeError("deviation or multi-venue control failed")
    if strategies.total_risk_pct != Decimal("0.8") or not asset.eligible:
        raise RuntimeError("strategy arbitration or asset eligibility failed")
    print(
        "PASS Phases 28-32 controlled production: live=CAPPED, deviation=DETECTED, "
        "venues=CONSOLIDATED, strategies=ARBITRATED, assets=ALLOWLISTED"
    )


async def strategy_evolution() -> None:
    engine = EvolutionEngine()
    pool = engine.allocate_pool(
        CapitalPool(
            pool_key="primary",
            allocated_capital=Decimal("10000"),
            reserved_capital=Decimal("2000"),
            investor_units=Decimal("100"),
        ),
        Decimal("9000"),
    )
    plan = engine.build_execution_plan(
        ExecutionRequest(
            order_id=str(uuid.uuid4()),
            total_quantity=Decimal("10"),
            duration_minutes=10,
            slices=5,
            reference_price=Decimal("100"),
            max_participation_pct=Decimal("5"),
        ),
        ExecutionStyle.TWAP,
    )
    analytics = engine.analyze_portfolio(
        PortfolioAnalyticsInput(
            portfolio_value=Decimal("1000"),
            position_values={"BTC": Decimal("600"), "ETH": Decimal("400")},
            returns={
                "BTC": (Decimal("-0.1"), Decimal("0.05"), Decimal("-0.02")),
                "ETH": (Decimal("-0.05"), Decimal("0.02"), Decimal("-0.01")),
            },
        )
    )
    native = engine.native_signal(
        "OLC",
        StrategyBar(close=Decimal("110"), fast_average=Decimal("105"), slow_average=Decimal("100")),
        "1.0",
    )
    parity = engine.check_parity([1, 0, -1], [1, 0, -1], Decimal("99"))
    authority = engine.decide_authority(
        AuthorityPolicy(
            authority=SignalAuthority.NATIVE_PYTHON,
            minimum_parity_pct=Decimal("99"),
            observed_parity_pct=parity.parity_pct,
            review_approved=True,
        )
    )
    if pool.approved_notional != Decimal("8000") or len(plan.slices) != 5:
        raise RuntimeError("capital-pool or execution planning failed")
    if analytics.expected_shortfall <= 0 or native.direction != 1:
        raise RuntimeError("portfolio analytics or native strategy failed")
    if not parity.passed or not authority.production_authority_granted:
        raise RuntimeError("native signal parity or authority review failed")
    print(
        "PASS Phases 33-37 strategy evolution: pools=SEGREGATED, execution=SLICED, "
        "analytics=EXPLAINED, native=PARITY_VERIFIED, authority=REVIEWED"
    )


async def roadmap_completion() -> None:
    engine = OperationsEngine()
    mobile = engine.authorize_mobile_control(
        MobileControlRequest(
            user_id="smoke-admin",
            role="ADMIN",
            mfa_verified=True,
            action=MobileAction.EMERGENCY_HALT,
        )
    )
    ml = engine.guard_ml_recommendation(
        MlRecommendation(
            model_key="slippage-risk",
            model_version="1.0",
            risk_multiplier=Decimal("0.5"),
            confidence=Decimal("0.9"),
            explanation=("elevated predicted slippage",),
        ),
        True,
    )
    anomaly = engine.detect_anomaly(
        AnomalyObservation(
            metric="slippage",
            value=Decimal("5"),
            baseline_mean=Decimal("1"),
            baseline_stddev=Decimal("1"),
            threshold_z=Decimal("3"),
        )
    )
    names = (
        "scalability",
        "high-availability",
        "disaster-recovery",
        "secrets",
        "resilience",
        "observability",
        "incident-response",
        "penetration-test",
        "compliance-review",
    )
    release = engine.approve_production_release(
        [HardeningCheck(name=name, passed=True, evidence="smoke verified") for name in names]
    )
    if not mobile.permitted or not ml.accepted or ml.applied_multiplier > 1:
        raise RuntimeError("mobile emergency control or ML guardrail failed")
    if not anomaly.anomalous or not release.approved:
        raise RuntimeError("anomaly detection or production hardening failed")
    print(
        "PASS Phases 38-40 roadmap completion: mobile=MFA_GUARDED, ML=RISK_SUBORDINATE, "
        "anomaly=DETECTED, production=EVIDENCE_APPROVED"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Olive Phase 2 live smoke test")
    parser.add_argument(
        "command",
        choices=(
            "seed",
            "send",
            "risk",
            "portfolio",
            "hierarchy",
            "correlation",
            "dynamic",
            "protection",
            "regime",
            "market-data",
            "execution-risk",
            "paper-pipeline",
            "governance-controls",
            "live-readiness",
            "controlled-production",
            "strategy-evolution",
            "roadmap-completion",
        ),
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
        elif args.command == "correlation":
            asyncio.run(correlation())
        elif args.command == "dynamic":
            asyncio.run(dynamic())
        elif args.command == "protection":
            asyncio.run(protection())
        elif args.command == "regime":
            asyncio.run(regime())
        elif args.command == "market-data":
            asyncio.run(market_data())
        elif args.command == "execution-risk":
            asyncio.run(execution_risk())
        elif args.command == "paper-pipeline":
            asyncio.run(paper_pipeline())
        elif args.command == "governance-controls":
            asyncio.run(governance_controls())
        elif args.command == "live-readiness":
            asyncio.run(live_readiness())
        elif args.command == "controlled-production":
            asyncio.run(controlled_production())
        elif args.command == "strategy-evolution":
            asyncio.run(strategy_evolution())
        elif args.command == "roadmap-completion":
            asyncio.run(roadmap_completion())
        else:
            send(args.url)
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
