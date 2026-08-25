from __future__ import annotations

from decimal import Decimal

from olive.production.schemas import (
    AssetEligibilityDecision,
    AssetProductionPolicy,
    DeviationReport,
    ExecutionObservation,
    LiveCapitalDecision,
    LiveCapitalPolicy,
    LiveOrderRequest,
    ProductionMode,
    StrategyAllocation,
    StrategyResolution,
    StrategySignal,
    VenueExposure,
    VenueQuote,
    VenueSelection,
)


class ControlledProductionEngine:
    """Hard gates that keep early production operation deliberately constrained."""

    def authorize_live_order(
        self, request: LiveOrderRequest, policy: LiveCapitalPolicy
    ) -> LiveCapitalDecision:
        reasons: list[str] = []
        if policy.mode is not ProductionMode.LIMITED_LIVE:
            reasons.append("LIVE_MODE_DISARMED")
        if not policy.readiness_approved:
            reasons.append("READINESS_NOT_APPROVED")
        if not policy.operator_armed:
            reasons.append("OPERATOR_NOT_ARMED")
        if request.strategy_key != policy.approved_strategy:
            reasons.append("STRATEGY_NOT_APPROVED")
        if request.instrument not in policy.approved_instruments:
            reasons.append("INSTRUMENT_NOT_APPROVED")
        if request.venue != policy.approved_venue:
            reasons.append("VENUE_NOT_APPROVED")
        if request.projected_total_exposure > policy.max_total_exposure:
            reasons.append("EXPOSURE_LIMIT")
        if request.projected_leverage > policy.max_leverage:
            reasons.append("LEVERAGE_LIMIT")
        approved_notional = min(request.requested_notional, policy.max_order_notional)
        if approved_notional < request.requested_notional:
            reasons.append("ORDER_NOTIONAL_REDUCED")
        blocking = tuple(reason for reason in reasons if reason != "ORDER_NOTIONAL_REDUCED")
        approved = not blocking
        return LiveCapitalDecision(
            signal_id=request.signal_id,
            approved=approved,
            approved_notional=approved_notional if approved else Decimal("0"),
            route_permitted=approved,
            reasons=tuple(reasons) if reasons else ("LIMITED_LIVE_APPROVED",),
        )

    def analyze_deviation(
        self,
        observation: ExecutionObservation,
        max_delay_delta_ms: int,
        max_slippage_pct: Decimal,
        max_pnl_divergence: Decimal,
    ) -> DeviationReport:
        missed = observation.live_fill_price is None
        slippage = None
        reasons: list[str] = []
        if not missed:
            assert observation.live_fill_price is not None
            slippage = abs(
                (observation.live_fill_price - observation.paper_fill_price)
                / observation.paper_fill_price
                * Decimal("100")
            ).quantize(Decimal("0.0001"))
        else:
            reasons.append("MISSED_FILL")
        delay_delta = observation.live_delay_ms - observation.paper_delay_ms
        pnl_divergence = observation.live_pnl - observation.paper_pnl
        if abs(delay_delta) > max_delay_delta_ms:
            reasons.append("DELAY_DEVIATION")
        if slippage is not None and slippage > max_slippage_pct:
            reasons.append("SLIPPAGE_DEVIATION")
        if abs(pnl_divergence) > max_pnl_divergence:
            reasons.append("PNL_DIVERGENCE")
        return DeviationReport(
            signal_id=observation.signal_id,
            delay_delta_ms=delay_delta,
            slippage_pct=slippage,
            fee_delta=observation.live_fee - observation.paper_fee,
            pnl_divergence=pnl_divergence,
            missed_fill=missed,
            breached=bool(reasons),
            reasons=tuple(reasons),
        )

    def select_venue(
        self, quotes: list[VenueQuote], requested_notional: Decimal, side: str
    ) -> VenueSelection:
        viable = [q for q in quotes if q.healthy and q.available_notional > 0]
        if not viable:
            return VenueSelection(
                venue=None,
                approved_notional=Decimal("0"),
                effective_price=None,
                reason="NO_HEALTHY_VENUE",
            )
        direction = Decimal("1") if side.upper() == "BUY" else Decimal("-1")
        chosen = min(viable, key=lambda q: q.price * (Decimal("1") + direction * q.fee_pct / 100))
        approved = min(requested_notional, chosen.available_notional)
        effective = chosen.price * (Decimal("1") + direction * chosen.fee_pct / 100)
        return VenueSelection(
            venue=chosen.venue,
            approved_notional=approved,
            effective_price=effective.quantize(Decimal("0.00000001")),
            reason="BEST_EFFECTIVE_PRICE"
            if approved == requested_notional
            else "VENUE_CAPACITY_REDUCED",
        )

    def consolidated_exposure(self, exposures: list[VenueExposure]) -> Decimal:
        return sum((item.gross_exposure for item in exposures), start=Decimal("0"))

    def resolve_strategies(
        self, signals: list[StrategySignal], portfolio_risk_budget_pct: Decimal
    ) -> StrategyResolution:
        if not signals:
            return StrategyResolution(
                instrument="", direction=0, allocations=(), total_risk_pct=Decimal("0")
            )
        winner_direction = max(signals, key=lambda signal: signal.priority).direction
        remaining = portfolio_risk_budget_pct
        allocations: list[StrategyAllocation] = []
        for signal in sorted(signals, key=lambda item: (-item.priority, item.strategy_key)):
            if signal.direction != winner_direction:
                allocations.append(
                    StrategyAllocation(
                        strategy_key=signal.strategy_key,
                        approved_risk_pct=Decimal("0"),
                        accepted=False,
                        reason="DIRECTION_CONFLICT",
                    )
                )
                continue
            approved = min(signal.requested_risk_pct, remaining)
            remaining -= approved
            allocations.append(
                StrategyAllocation(
                    strategy_key=signal.strategy_key,
                    approved_risk_pct=approved,
                    accepted=approved > 0,
                    reason="PORTFOLIO_BUDGET"
                    if approved < signal.requested_risk_pct
                    else "APPROVED",
                )
            )
        total = portfolio_risk_budget_pct - remaining
        return StrategyResolution(
            instrument=signals[0].instrument,
            direction=winner_direction,
            allocations=tuple(allocations),
            total_risk_pct=total,
        )

    def check_asset_eligibility(
        self,
        instrument: str,
        venue: str,
        requested_notional: Decimal,
        policy: AssetProductionPolicy,
    ) -> AssetEligibilityDecision:
        reasons: list[str] = []
        if not policy.enabled:
            reasons.append("ASSET_CLASS_DISABLED")
        if instrument not in policy.approved_instruments:
            reasons.append("INSTRUMENT_NOT_APPROVED")
        if venue not in policy.approved_venues:
            reasons.append("VENUE_NOT_APPROVED")
        approved = not reasons
        notional = min(requested_notional, policy.max_notional) if approved else Decimal("0")
        if approved and notional < requested_notional:
            reasons.append("ASSET_NOTIONAL_REDUCED")
        return AssetEligibilityDecision(
            eligible=approved,
            approved_notional=notional,
            reasons=tuple(reasons) if reasons else ("ASSET_PRODUCTION_APPROVED",),
        )
