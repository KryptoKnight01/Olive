from __future__ import annotations

from decimal import Decimal

from olive.readiness.schemas import (
    EventDecision,
    EventObservation,
    EventRiskPolicy,
    HealthStatus,
    PerformanceAssessment,
    PerformanceMetrics,
    PerformanceThresholds,
    ReadinessCheck,
    ReadinessReview,
    ShadowOrder,
    ShadowResult,
    StressInput,
    StressResult,
    StressScenario,
)


class LiveReadinessEngine:
    """Deterministic controls used before Olive is allowed to trade live capital."""

    def assess_performance(
        self, metrics: PerformanceMetrics, thresholds: PerformanceThresholds
    ) -> PerformanceAssessment:
        breaches: list[str] = []
        if metrics.trades < thresholds.min_trades:
            breaches.append("INSUFFICIENT_SAMPLE")
        if metrics.profit_factor < thresholds.min_profit_factor:
            breaches.append("PROFIT_FACTOR")
        if metrics.expectancy_r < thresholds.min_expectancy_r:
            breaches.append("EXPECTANCY")
        if metrics.max_drawdown_pct > thresholds.max_drawdown_pct:
            breaches.append("DRAWDOWN")
        if metrics.slippage_pct > thresholds.max_slippage_pct:
            breaches.append("SLIPPAGE")
        if not breaches:
            status = HealthStatus.GREEN
        elif "DRAWDOWN" in breaches or len(breaches) >= 3:
            status = HealthStatus.RED
        elif len(breaches) == 2:
            status = HealthStatus.ORANGE
        else:
            status = HealthStatus.YELLOW
        return PerformanceAssessment(
            strategy_key=metrics.strategy_key, status=status, breaches=tuple(breaches)
        )

    def run_stress_test(self, portfolio: StressInput, scenario: StressScenario) -> StressResult:
        liquidity_factor = Decimal("1") + scenario.liquidity_reduction_pct / Decimal("100")
        market_shock = scenario.gap_pct / Decimal("100")
        loss = (
            portfolio.gross_exposure
            * market_shock
            * scenario.volatility_multiplier
            * scenario.correlation_multiplier
            * liquidity_factor
        )
        if scenario.venue_failure:
            loss *= Decimal("1.25")
        loss_pct = loss / portfolio.portfolio_value * Decimal("100")
        shortfall = max(Decimal("0"), loss - portfolio.available_margin)
        contributors = ["GAP", "VOLATILITY", "CORRELATION", "LIQUIDITY"]
        if scenario.venue_failure:
            contributors.append("VENUE_FAILURE")
        return StressResult(
            scenario=scenario.name,
            projected_loss=loss.quantize(Decimal("0.01")),
            projected_loss_pct=loss_pct.quantize(Decimal("0.01")),
            margin_shortfall=shortfall.quantize(Decimal("0.01")),
            blocked=loss_pct > portfolio.max_loss_pct or shortfall > 0,
            contributors=tuple(contributors),
        )

    def evaluate_event(
        self, observation: EventObservation, policy: EventRiskPolicy
    ) -> EventDecision:
        minutes = observation.minutes_from_event
        in_blackout = -policy.blackout_minutes_after <= minutes <= policy.blackout_minutes_before
        return EventDecision(
            event_key=observation.event_key,
            entries_allowed=not in_blackout,
            risk_multiplier=Decimal("0") if in_blackout else policy.risk_multiplier,
            close_before_event=(
                in_blackout and observation.open_position and not policy.allow_hold_through
            ),
            reason="EVENT_BLACKOUT" if in_blackout else "EVENT_RISK_MULTIPLIER",
        )

    def simulate_shadow(self, order: ShadowOrder, slippage_pct: Decimal) -> ShadowResult:
        direction = Decimal("1") if order.side.upper() == "BUY" else Decimal("-1")
        fill = order.reference_price * (Decimal("1") + direction * slippage_pct / Decimal("100"))
        return ShadowResult(
            signal_id=order.signal_id,
            hypothetical_fill_price=fill.quantize(Decimal("0.00000001")),
            hypothetical_notional=(fill * order.quantity).quantize(Decimal("0.01")),
            sent_to_venue=False,
            status="SHADOW_ONLY",
        )

    def review(self, checks: list[ReadinessCheck]) -> ReadinessReview:
        failures = tuple(check.name for check in checks if check.mandatory and not check.passed)
        return ReadinessReview(approved=not failures, failed_checks=failures, checks=tuple(checks))
