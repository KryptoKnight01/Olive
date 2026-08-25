from uuid import uuid4

import pytest

from olive.risk.regime import PortfolioRegimeEngine
from olive.risk.schemas import PortfolioRegime, PortfolioRegimeInput, PortfolioRegimePolicy


def policy(**changes: object) -> PortfolioRegimePolicy:
    threshold = {
        "calm_maximum": "10",
        "elevated_minimum": "20",
        "high_volatility_minimum": "30",
        "crisis_minimum": "40",
    }
    values: dict[str, object] = {
        "thresholds": {
            "realized_volatility_pct": threshold,
            "average_absolute_correlation": {
                "calm_maximum": "0.2",
                "elevated_minimum": "0.5",
                "high_volatility_minimum": "0.7",
                "crisis_minimum": "0.9",
            },
            "portfolio_drawdown_pct": threshold,
            "liquidity_stress_score": threshold,
            "market_stress_score": threshold,
        },
        "controls": {
            "CALM": {"risk_multiplier": "1", "max_leverage": "3", "max_new_positions": 10},
            "NORMAL": {"risk_multiplier": "1", "max_leverage": "3", "max_new_positions": 8},
            "ELEVATED": {"risk_multiplier": "0.75", "max_leverage": "2", "max_new_positions": 4},
            "HIGH_VOLATILITY": {
                "risk_multiplier": "0.5",
                "max_leverage": "1.5",
                "max_new_positions": 2,
            },
            "CRISIS": {"risk_multiplier": "0", "max_leverage": "0", "max_new_positions": 0},
        },
    }
    values.update(changes)
    return PortfolioRegimePolicy.model_validate(values)


def request(**changes: object) -> PortfolioRegimeInput:
    values: dict[str, object] = {
        "observation_id": uuid4(),
        "realized_volatility_pct": "15",
        "average_absolute_correlation": "0.3",
        "portfolio_drawdown_pct": "2",
        "liquidity_stress_score": "5",
        "market_stress_score": "5",
    }
    values.update(changes)
    return PortfolioRegimeInput.model_validate(values)


def test_normal_regime_uses_normal_controls() -> None:
    decision = PortfolioRegimeEngine().evaluate(request(), policy())
    assert decision.regime is PortfolioRegime.NORMAL
    assert decision.controls.max_new_positions == 8


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"realized_volatility_pct": "22"}, PortfolioRegime.ELEVATED),
        ({"average_absolute_correlation": "0.75"}, PortfolioRegime.HIGH_VOLATILITY),
        ({"market_stress_score": "45"}, PortfolioRegime.CRISIS),
    ],
)
def test_highest_metric_severity_wins(change: dict[str, str], expected: PortfolioRegime) -> None:
    assert PortfolioRegimeEngine().evaluate(request(**change), policy()).regime is expected


def test_calm_requires_every_metric_to_be_calm() -> None:
    decision = PortfolioRegimeEngine().evaluate(
        request(realized_volatility_pct="5", average_absolute_correlation="0.1"), policy()
    )
    assert decision.regime is PortfolioRegime.CALM


def test_missing_thresholds_fail_closed() -> None:
    bad = policy().model_dump()
    del bad["thresholds"]["market_stress_score"]
    with pytest.raises(ValueError, match="missing"):
        PortfolioRegimeEngine().evaluate(request(), PortfolioRegimePolicy.model_validate(bad))
