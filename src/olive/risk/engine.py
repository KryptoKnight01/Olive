from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from olive.risk.schemas import (
    RiskDecisionOutcome,
    SingleTradeRiskDecision,
    SingleTradeRiskInput,
    SingleTradeRiskPolicy,
)

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


class SingleTradeRiskEngine:
    def evaluate(
        self, request: SingleTradeRiskInput, policy: SingleTradeRiskPolicy
    ) -> SingleTradeRiskDecision:
        stop_distance = abs(request.entry_price - request.stop_price)
        stop_distance_pct = stop_distance / request.entry_price * HUNDRED
        limits = self._limits(request, policy, stop_distance_pct)
        base = min(request.requested_risk_pct, policy.base_risk_pct, policy.max_risk_pct)

        if request.entry_price == request.stop_price:
            return self._rejected(request, policy, limits, "stop price equals entry price")
        if stop_distance_pct < policy.min_stop_distance_pct:
            return self._rejected(request, policy, limits, "stop distance is below the minimum")
        if stop_distance_pct > policy.max_stop_distance_pct:
            return self._rejected(request, policy, limits, "stop distance exceeds the maximum")
        if policy.base_risk_pct > policy.max_risk_pct:
            return self._rejected(request, policy, limits, "risk policy is internally inconsistent")

        risk_budget = request.equity * base / HUNDRED
        risk_per_unit = stop_distance * request.contract_multiplier
        stop_size = risk_budget / risk_per_unit
        effective_leverage = min(
            policy.max_leverage,
            request.instrument_max_leverage or policy.max_leverage,
        )
        unit_notional = request.entry_price * request.contract_multiplier
        size_caps = {
            "stop risk": stop_size,
            "trade notional": policy.max_notional / unit_notional,
            "leverage": request.equity * effective_leverage / unit_notional,
            "margin": min(request.available_margin, policy.max_margin)
            * effective_leverage
            / unit_notional,
        }
        binding_name, raw_size = min(size_caps.items(), key=lambda item: item[1])
        position_size = self._floor_lot(raw_size, request.lot_size)
        if position_size <= ZERO:
            return self._rejected(
                request, policy, limits, "all applicable caps reduce size below one lot"
            )

        approved_risk_pct = (position_size * risk_per_unit / request.equity * HUNDRED).quantize(
            Decimal("0.00000001")
        )
        reduced = position_size < self._floor_lot(stop_size, request.lot_size)
        reasons = [
            f"stop-based size calculated from {base}% risk",
            f"binding size constraint: {binding_name}",
        ]
        if request.requested_risk_pct > base:
            reduced = True
            reasons.append("requested risk was capped by base/maximum trade risk")
        return SingleTradeRiskDecision(
            decision=(
                RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
                if reduced
                else RiskDecisionOutcome.APPROVED
            ),
            signal_id=request.signal_id,
            requested_risk_pct=request.requested_risk_pct,
            approved_risk_pct=approved_risk_pct,
            position_size=position_size,
            base_risk_pct=policy.base_risk_pct,
            multipliers={
                "regime": ONE,
                "correlation": ONE,
                "drawdown": ONE,
                "liquidity": ONE,
                "strategy_health": ONE,
                "event_risk": ONE,
            },
            limits=limits,
            reasons=reasons,
        )

    @staticmethod
    def _floor_lot(value: Decimal, lot_size: Decimal) -> Decimal:
        return (value / lot_size).to_integral_value(rounding=ROUND_DOWN) * lot_size

    @staticmethod
    def _limits(
        request: SingleTradeRiskInput,
        policy: SingleTradeRiskPolicy,
        stop_distance_pct: Decimal,
    ) -> dict[str, Decimal | None]:
        return {
            "trade_risk_pct": policy.max_risk_pct,
            "instrument_notional": policy.max_notional,
            "strategy": None,
            "asset_class": None,
            "correlation_cluster": None,
            "portfolio": None,
            "margin": min(request.available_margin, policy.max_margin),
            "venue": None,
            "leverage": min(
                policy.max_leverage,
                request.instrument_max_leverage or policy.max_leverage,
            ),
            "stop_distance_pct": stop_distance_pct,
        }

    def _rejected(
        self,
        request: SingleTradeRiskInput,
        policy: SingleTradeRiskPolicy,
        limits: dict[str, Decimal | None],
        reason: str,
    ) -> SingleTradeRiskDecision:
        return SingleTradeRiskDecision(
            decision=RiskDecisionOutcome.REJECTED,
            signal_id=request.signal_id,
            requested_risk_pct=request.requested_risk_pct,
            approved_risk_pct=ZERO,
            position_size=ZERO,
            base_risk_pct=policy.base_risk_pct,
            multipliers={
                "regime": ONE,
                "correlation": ONE,
                "drawdown": ONE,
                "liquidity": ONE,
                "strategy_health": ONE,
                "event_risk": ONE,
            },
            limits=limits,
            reasons=[reason],
        )
