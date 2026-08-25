from __future__ import annotations

from decimal import Decimal

from olive.risk.schemas import DynamicRiskDecision, DynamicRiskInput, DynamicRiskPolicy

ONE = Decimal("1")


class DynamicRiskMultiplierEngine:
    """Combine bounded risk multipliers without allowing them to override hard caps."""

    def evaluate(
        self, request: DynamicRiskInput, policy: DynamicRiskPolicy
    ) -> DynamicRiskDecision:
        raw = {
            "regime": request.regime,
            "correlation": request.correlation,
            "drawdown": request.drawdown,
            "liquidity": request.liquidity,
            "signal_quality": request.signal_quality,
            "strategy_health": request.strategy_health,
            "event_risk": request.event_risk,
        }
        bounds = {
            "regime": policy.regime,
            "correlation": policy.correlation,
            "drawdown": policy.drawdown,
            "liquidity": policy.liquidity,
            "signal_quality": policy.signal_quality,
            "strategy_health": policy.strategy_health,
            "event_risk": policy.event_risk,
        }
        if any(value.minimum > value.maximum for value in bounds.values()):
            raise ValueError("dynamic risk multiplier policy is internally inconsistent")
        bounded = {
            name: min(bounds[name].maximum, max(bounds[name].minimum, value))
            for name, value in raw.items()
        }
        product = ONE
        for value in bounded.values():
            product *= value
        uncapped = request.base_risk_pct * product
        final = min(uncapped, request.base_risk_pct, request.hard_max_risk_pct)
        reasons = ["bounded dynamic multipliers applied"]
        if final < uncapped:
            reasons.append("base or hard maximum risk cap overrode multiplier result")
        if any(raw[name] != bounded[name] for name in raw):
            reasons.append("one or more multiplier inputs were bounded by policy")
        return DynamicRiskDecision(
            signal_id=request.signal_id,
            base_risk_pct=request.base_risk_pct,
            raw_multipliers=raw,
            bounded_multipliers=bounded,
            multiplier_product=product,
            uncapped_risk_pct=uncapped,
            final_risk_pct=final,
            caps={
                "base_risk_pct": request.base_risk_pct,
                "hard_max_risk_pct": request.hard_max_risk_pct,
            },
            reasons=reasons,
        )
