from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from olive.config import AppEnvironment, get_settings
from olive.db import create_database_engine, create_session_factory
from olive.domain.models import Strategy, StrategyVersion
from olive.paper.models import PaperPipelineRunRecord
from olive.risk.models import SingleTradeRiskPolicyRecord
from olive.validation.models import SignalValidationPolicy


@dataclass(frozen=True)
class PaperStrategy:
    code: str
    name: str
    code_hash: str
    setup_score: str


PAPER_STRATEGIES = (
    PaperStrategy("OLM", "Olive Mean Reversion", "1" * 64, "81.0"),
    PaperStrategy("OLB", "Olive Breakout", "2" * 64, "84.0"),
)


async def seed_strategies() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    created: list[str] = []
    try:
        async with sessions() as session:
            for definition in PAPER_STRATEGIES:
                strategy = await session.scalar(
                    select(Strategy).where(Strategy.code == definition.code)
                )
                if strategy is None:
                    strategy = Strategy(code=definition.code, name=definition.name)
                    session.add(strategy)
                    await session.flush()

                version = await session.scalar(
                    select(StrategyVersion).where(
                        StrategyVersion.strategy_id == strategy.id,
                        StrategyVersion.version == "1.0.0",
                    )
                )
                if version is not None:
                    continue

                version = StrategyVersion(
                    strategy_id=strategy.id,
                    version="1.0.0",
                    code_hash=definition.code_hash,
                    configuration_version="smoke-1",
                )
                session.add(version)
                await session.flush()
                session.add_all(
                    [
                        SignalValidationPolicy(
                            strategy_version_id=version.id,
                            allowed_timeframes=["15m"],
                            max_entry_deviation_pct=Decimal("1.0"),
                            min_expected_rr=Decimal("1.5"),
                            min_setup_score=Decimal("70"),
                        ),
                        SingleTradeRiskPolicyRecord(
                            strategy_version_id=version.id,
                            base_risk_pct=Decimal("1"),
                            max_risk_pct=Decimal("1.5"),
                            max_notional=Decimal("100000"),
                            max_leverage=Decimal("3"),
                            max_margin=Decimal("50000"),
                            min_stop_distance_pct=Decimal("0.25"),
                            max_stop_distance_pct=Decimal("10"),
                        ),
                    ]
                )
                created.append(definition.code)
            await session.commit()
    finally:
        await engine.dispose()

    if created:
        print(f"PASS registered paper strategies: {', '.join(created)}")
    else:
        print("PASS paper strategies already registered")


def make_alert_payload(
    strategy: PaperStrategy, secret: str, now: datetime | None = None
) -> tuple[bytes, str]:
    emitted_at = (now or datetime.now(UTC)).astimezone(UTC)
    external_signal_id = f"{strategy.code}-BTCUSD-{uuid.uuid4()}"
    payload: dict[str, Any] = {
        "webhook_secret": secret,
        "schema_version": "1.0",
        "signal_id": external_signal_id,
        "strategy_id": strategy.code,
        "strategy_version": "1.0.0",
        "configuration_version": "smoke-1",
        "environment": "staging",
        "timestamp": emitted_at.isoformat(),
        "expiry_seconds": 300,
        "venue": "COINBASE",
        "instrument": "BTC-USD",
        "direction": "LONG",
        "entry_price": "65000.00",
        "reference_price": "65000.00",
        "stop": "64000.00",
        "targets": ["67000.00", "68000.00"],
        "expected_rr": "2.0",
        "timeframe": "15m",
        "setup_score": strategy.setup_score,
        "regime": "NORMAL",
        "metadata": {"confidence": "0.75"},
    }
    return json.dumps(payload, separators=(",", ":")).encode(), external_signal_id


def post_alert(url: str, body: bytes) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Olive-Staging-Smoke"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


async def wait_for_execution(signal_id: uuid.UUID) -> PaperPipelineRunRecord:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        for _attempt in range(30):
            async with sessions() as session:
                execution = await session.scalar(
                    select(PaperPipelineRunRecord).where(
                        PaperPipelineRunRecord.signal_id == signal_id
                    )
                )
                if execution is not None:
                    return execution
            await asyncio.sleep(1)
    finally:
        await engine.dispose()
    raise RuntimeError(f"paper execution did not complete for signal {signal_id}")


async def run(url: str) -> None:
    settings = get_settings()
    if settings.app_env is not AppEnvironment.STAGING:
        raise RuntimeError("multi-strategy smoke test requires OLIVE_APP_ENV=staging")
    configured = settings.tradingview_webhook_secret
    secret = configured.get_secret_value() if configured is not None else ""
    if len(secret) < 32:
        raise RuntimeError("OLIVE_TRADINGVIEW_WEBHOOK_SECRET is not configured")

    await seed_strategies()
    for strategy in PAPER_STRATEGIES:
        body, external_id = make_alert_payload(strategy, secret)
        status, response = await asyncio.to_thread(post_alert, url, body)
        if status != 202:
            raise RuntimeError(
                f"{strategy.code} signal was rejected: {status} "
                f"{response.get('code', response)}"
            )
        signal_id = uuid.UUID(str(response["signal_id"]))
        execution = await wait_for_execution(signal_id)
        if (
            execution.order_status != "FILLED"
            or execution.protection_status != "PROTECTED"
            or not execution.reconciled
        ):
            raise RuntimeError(f"{strategy.code} paper execution did not complete safely")
        print(
            f"PASS {strategy.code}: accepted={external_id}, filled, protected, reconciled, "
            f"paper_pnl={execution.realized_pnl}"
        )
    print("PASS multi-strategy paper test completed; live routing remains disarmed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Olive multi-strategy staging paper test")
    parser.add_argument("--url", required=True, help="Public TradingView alert bridge URL")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.url))
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
