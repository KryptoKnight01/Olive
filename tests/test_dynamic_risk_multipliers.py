from decimal import Decimal
from uuid import uuid4

import pytest

from olive.risk.multipliers import DynamicRiskMultiplierEngine
from olive.risk.schemas import DynamicRiskInput, DynamicRiskPolicy


def policy(**changes: object) -> DynamicRiskPolicy:
    standard = {"minimum": "0.25", "maximum": "1.25"}
    values: dict[str, object] = {
        name: standard
        for name in (
            "regime", "correlation", "drawdown", "liquidity", "signal_quality",
            "strategy_health", "event_risk",
        )
    }
    values.update(changes)
    return DynamicRiskPolicy.model_validate(values)


def request(**changes: object) -> DynamicRiskInput:
    values: dict[str, object] = {
        "signal_id": uuid4(), "base_risk_pct": "1", "hard_max_risk_pct": "1.5",
        "regime": "1", "correlation": "1", "drawdown": "1", "liquidity": "1",
        "signal_quality": "1", "strategy_health": "1", "event_risk": "1",
    }
    values.update(changes)
    return DynamicRiskInput.model_validate(values)


def test_neutral_multipliers_preserve_base_risk() -> None:
    decision = DynamicRiskMultiplierEngine().evaluate(request(), policy())
    assert decision.final_risk_pct == 1
    assert decision.multiplier_product == 1


def test_throttles_multiply_transparently() -> None:
    decision = DynamicRiskMultiplierEngine().evaluate(
        request(regime="0.8", drawdown="0.5", liquidity="0.5"), policy()
    )
    assert decision.multiplier_product == Decimal("0.200")
    assert decision.final_risk_pct == Decimal("0.200")


def test_base_risk_is_a_ceiling_not_an_entitlement() -> None:
    decision = DynamicRiskMultiplierEngine().evaluate(
        request(regime="1.2", signal_quality="1.2"), policy()
    )
    assert decision.uncapped_risk_pct == Decimal("1.44")
    assert decision.final_risk_pct == Decimal("1")


def test_inputs_are_bounded_and_evidenced() -> None:
    decision = DynamicRiskMultiplierEngine().evaluate(request(event_risk="0.1"), policy())
    assert decision.bounded_multipliers["event_risk"] == Decimal("0.25")
    assert "one or more multiplier inputs were bounded by policy" in decision.reasons


def test_inconsistent_bounds_fail_closed() -> None:
    with pytest.raises(ValueError, match="internally inconsistent"):
        DynamicRiskMultiplierEngine().evaluate(
            request(), policy(regime={"minimum": "1", "maximum": "0.5"})
        )
