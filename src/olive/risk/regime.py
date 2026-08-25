from __future__ import annotations

from decimal import Decimal

from olive.risk.schemas import (
    PortfolioRegime,
    PortfolioRegimeDecision,
    PortfolioRegimeInput,
    PortfolioRegimePolicy,
    RegimeThresholds,
)

SEVERITY = {
    PortfolioRegime.CALM: 0,
    PortfolioRegime.NORMAL: 1,
    PortfolioRegime.ELEVATED: 2,
    PortfolioRegime.HIGH_VOLATILITY: 3,
    PortfolioRegime.CRISIS: 4,
}


class PortfolioRegimeEngine:
    """Classify portfolio regime from transparent measurable inputs."""

    def evaluate(
        self, request: PortfolioRegimeInput, policy: PortfolioRegimePolicy
    ) -> PortfolioRegimeDecision:
        metrics = {
            "realized_volatility_pct": request.realized_volatility_pct,
            "average_absolute_correlation": request.average_absolute_correlation,
            "portfolio_drawdown_pct": request.portfolio_drawdown_pct,
            "liquidity_stress_score": request.liquidity_stress_score,
            "market_stress_score": request.market_stress_score,
        }
        missing = sorted(set(metrics).difference(policy.thresholds))
        if missing:
            raise ValueError(f"regime thresholds missing for: {', '.join(missing)}")
        if set(PortfolioRegime).difference(policy.controls):
            raise ValueError("regime controls are incomplete")
        metric_regimes = {
            name: self._classify(value, policy.thresholds[name])
            for name, value in metrics.items()
        }
        regime = max(metric_regimes.values(), key=SEVERITY.__getitem__)
        binding = sorted(name for name, value in metric_regimes.items() if value is regime)
        return PortfolioRegimeDecision(
            observation_id=request.observation_id,
            regime=regime,
            metrics=metrics,
            metric_regimes=metric_regimes,
            controls=policy.controls[regime],
            reasons=[f"highest severity triggered by: {', '.join(binding)}"],
        )

    @staticmethod
    def _classify(value: Decimal, thresholds: RegimeThresholds) -> PortfolioRegime:
        numeric = value
        if not (
            thresholds.calm_maximum
            < thresholds.elevated_minimum
            < thresholds.high_volatility_minimum
            < thresholds.crisis_minimum
        ):
            raise ValueError("regime thresholds are internally inconsistent")
        if numeric >= thresholds.crisis_minimum:
            return PortfolioRegime.CRISIS
        if numeric >= thresholds.high_volatility_minimum:
            return PortfolioRegime.HIGH_VOLATILITY
        if numeric >= thresholds.elevated_minimum:
            return PortfolioRegime.ELEVATED
        if numeric <= thresholds.calm_maximum:
            return PortfolioRegime.CALM
        return PortfolioRegime.NORMAL
