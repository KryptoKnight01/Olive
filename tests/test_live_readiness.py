from decimal import Decimal

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


def test_healthy_strategy_is_green() -> None:
    result = LiveReadinessEngine().assess_performance(
        PerformanceMetrics(
            strategy_key="olive",
            profit_factor=Decimal("1.8"),
            win_rate=Decimal("55"),
            expectancy_r=Decimal("0.3"),
            average_r=Decimal("0.4"),
            max_drawdown_pct=Decimal("8"),
            trades=100,
            slippage_pct=Decimal("0.1"),
        ),
        PerformanceThresholds(),
    )
    assert result.status is HealthStatus.GREEN
    assert result.breaches == ()


def test_multiple_strategy_breaches_are_red() -> None:
    result = LiveReadinessEngine().assess_performance(
        PerformanceMetrics(
            strategy_key="olive",
            profit_factor=Decimal("0.8"),
            win_rate=Decimal("30"),
            expectancy_r=Decimal("-0.2"),
            average_r=Decimal("-0.1"),
            max_drawdown_pct=Decimal("20"),
            trades=10,
            slippage_pct=Decimal("2"),
        ),
        PerformanceThresholds(),
    )
    assert result.status is HealthStatus.RED
    assert "DRAWDOWN" in result.breaches


def test_stress_loss_blocks_portfolio() -> None:
    result = LiveReadinessEngine().run_stress_test(
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
    assert result.blocked is True
    assert "VENUE_FAILURE" in result.contributors


def test_event_blackout_stops_entries_and_requires_exit() -> None:
    result = LiveReadinessEngine().evaluate_event(
        EventObservation(event_key="FOMC", minutes_from_event=5, open_position=True),
        EventRiskPolicy(
            blackout_minutes_before=30, blackout_minutes_after=15, risk_multiplier=Decimal("0.5")
        ),
    )
    assert result.entries_allowed is False
    assert result.risk_multiplier == 0
    assert result.close_before_event is True


def test_outside_event_window_applies_multiplier() -> None:
    result = LiveReadinessEngine().evaluate_event(
        EventObservation(event_key="CPI", minutes_from_event=60),
        EventRiskPolicy(
            blackout_minutes_before=30, blackout_minutes_after=15, risk_multiplier=Decimal("0.5")
        ),
    )
    assert result.entries_allowed is True
    assert result.risk_multiplier == Decimal("0.5")


def test_shadow_order_never_routes_to_venue() -> None:
    result = LiveReadinessEngine().simulate_shadow(
        ShadowOrder(
            signal_id="sig-1",
            strategy_key="olive",
            instrument="BTCUSDT",
            side="BUY",
            quantity=Decimal("2"),
            reference_price=Decimal("100"),
        ),
        Decimal("0.5"),
    )
    assert result.hypothetical_fill_price == Decimal("100.50000000")
    assert result.sent_to_venue is False
    assert result.status == "SHADOW_ONLY"


def test_readiness_requires_every_mandatory_check() -> None:
    result = LiveReadinessEngine().review(
        [
            ReadinessCheck(name="security", passed=True, evidence="scan passed"),
            ReadinessCheck(name="reconciliation", passed=False, evidence="difference found"),
            ReadinessCheck(
                name="optional-report", passed=False, evidence="pending", mandatory=False
            ),
        ]
    )
    assert result.approved is False
    assert result.failed_checks == ("reconciliation",)


def test_readiness_approves_complete_evidence() -> None:
    names = (
        "security",
        "risk",
        "execution",
        "reconciliation",
        "backup",
        "monitoring",
        "kill-switch",
        "incident-response",
    )
    result = LiveReadinessEngine().review(
        [ReadinessCheck(name=name, passed=True, evidence="verified") for name in names]
    )
    assert result.approved is True
    assert result.failed_checks == ()
