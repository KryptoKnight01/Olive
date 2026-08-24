from __future__ import annotations

from decimal import Decimal

from olive.risk.schemas import (
    PortfolioRiskDecision,
    PortfolioRiskInput,
    PortfolioRiskPolicy,
    PositionSide,
    RiskDecisionOutcome,
)

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


class PortfolioRiskEngine:
    """Evaluate a proposed trade against projected post-trade portfolio state."""

    def evaluate(
        self, request: PortfolioRiskInput, policy: PortfolioRiskPolicy
    ) -> PortfolioRiskDecision:
        current = self._current_metrics(request)
        limits = self._limits(request.equity, policy)
        if len(request.positions) >= policy.max_concurrent_positions:
            return self._decision(
                request, current, limits, ZERO, "concurrent-position limit reached"
            )

        long_now = Decimal(current["long_exposure"])
        short_now = Decimal(current["short_exposure"])
        signed_now = long_now - short_now
        direction = ONE if request.proposed_side is PositionSide.LONG else -ONE
        capacities = {
            "gross exposure": (
                Decimal(limits["gross_exposure"]) - Decimal(current["gross_exposure"])
            ),
            "side exposure": (
                Decimal(limits["long_exposure"]) - long_now
                if request.proposed_side is PositionSide.LONG
                else Decimal(limits["short_exposure"]) - short_now
            ),
            "leverage": Decimal(limits["leverage_notional"]) - Decimal(current["gross_exposure"]),
        }
        fractions = {
            name: capacity / request.proposed_notional for name, capacity in capacities.items()
        }
        fractions["open stop risk"] = (
            Decimal(limits["open_stop_risk"]) - Decimal(current["open_stop_risk"])
        ) / request.proposed_stop_risk
        if request.proposed_margin > ZERO:
            fractions["margin utilization"] = (
                Decimal(limits["margin_used"]) - Decimal(current["margin_used"])
            ) / request.proposed_margin

        net_limit = Decimal(limits["net_exposure"])
        proposed_signed = direction * request.proposed_notional
        if proposed_signed > ZERO:
            fractions["net exposure"] = (net_limit - signed_now) / proposed_signed
        else:
            fractions["net exposure"] = (-net_limit - signed_now) / proposed_signed

        binding, fraction = min(fractions.items(), key=lambda item: item[1])
        fraction = min(ONE, max(ZERO, fraction))
        reason = (
            "all projected portfolio limits satisfied"
            if fraction == ONE
            else f"binding projected portfolio limit: {binding}"
        )
        return self._decision(request, current, limits, fraction, reason)

    @staticmethod
    def _current_metrics(request: PortfolioRiskInput) -> dict[str, Decimal | int]:
        long_exposure = sum(
            (
                position.notional
                for position in request.positions
                if position.side is PositionSide.LONG
            ),
            ZERO,
        )
        short_exposure = sum(
            (
                position.notional
                for position in request.positions
                if position.side is PositionSide.SHORT
            ),
            ZERO,
        )
        gross = long_exposure + short_exposure
        return {
            "equity": request.equity,
            "gross_exposure": gross,
            "net_exposure": long_exposure - short_exposure,
            "long_exposure": long_exposure,
            "short_exposure": short_exposure,
            "open_stop_risk": sum((position.stop_risk for position in request.positions), ZERO),
            "margin_used": sum((position.margin_used for position in request.positions), ZERO),
            "leverage": gross / request.equity,
            "position_count": len(request.positions),
        }

    @staticmethod
    def _limits(equity: Decimal, policy: PortfolioRiskPolicy) -> dict[str, Decimal | int]:
        return {
            "gross_exposure": equity * policy.max_gross_exposure_pct / HUNDRED,
            "net_exposure": equity * policy.max_net_exposure_pct / HUNDRED,
            "long_exposure": equity * policy.max_long_exposure_pct / HUNDRED,
            "short_exposure": equity * policy.max_short_exposure_pct / HUNDRED,
            "open_stop_risk": equity * policy.max_open_stop_risk_pct / HUNDRED,
            "margin_used": equity * policy.max_margin_utilization_pct / HUNDRED,
            "leverage": policy.max_leverage,
            "leverage_notional": equity * policy.max_leverage,
            "position_count": policy.max_concurrent_positions,
        }

    def _decision(
        self,
        request: PortfolioRiskInput,
        current: dict[str, Decimal | int],
        limits: dict[str, Decimal | int],
        fraction: Decimal,
        reason: str,
    ) -> PortfolioRiskDecision:
        proposed_notional = request.proposed_notional * fraction
        long_exposure = Decimal(current["long_exposure"])
        short_exposure = Decimal(current["short_exposure"])
        if request.proposed_side is PositionSide.LONG:
            long_exposure += proposed_notional
        else:
            short_exposure += proposed_notional
        gross = long_exposure + short_exposure
        projected: dict[str, Decimal | int] = {
            "equity": request.equity,
            "gross_exposure": gross,
            "net_exposure": long_exposure - short_exposure,
            "long_exposure": long_exposure,
            "short_exposure": short_exposure,
            "open_stop_risk": Decimal(current["open_stop_risk"])
            + request.proposed_stop_risk * fraction,
            "margin_used": Decimal(current["margin_used"]) + request.proposed_margin * fraction,
            "leverage": gross / request.equity,
            "position_count": int(current["position_count"]) + (1 if fraction > ZERO else 0),
        }
        outcome = (
            RiskDecisionOutcome.REJECTED
            if fraction == ZERO
            else RiskDecisionOutcome.APPROVED
            if fraction == ONE
            else RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
        )
        return PortfolioRiskDecision(
            decision=outcome,
            signal_id=request.signal_id,
            approved_fraction=fraction,
            approved_notional=proposed_notional,
            current=current,
            projected=projected,
            limits=limits,
            reasons=[reason],
        )
