from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from olive.risk.engine import SingleTradeRiskEngine
from olive.risk.schemas import (
    RiskDecisionOutcome,
    SingleTradeRiskInput,
    SingleTradeRiskPolicy,
)


def request(**changes: object) -> SingleTradeRiskInput:
    values: dict[str, object] = {
        "signal_id": uuid.uuid4(),
        "equity": Decimal("100000"),
        "available_margin": Decimal("50000"),
        "entry_price": Decimal("100"),
        "stop_price": Decimal("98"),
        "requested_risk_pct": Decimal("1"),
        "contract_multiplier": Decimal("1"),
        "lot_size": Decimal("1"),
        "instrument_max_leverage": Decimal("5"),
    }
    values.update(changes)
    return SingleTradeRiskInput.model_validate(values)


def policy(**changes: object) -> SingleTradeRiskPolicy:
    values: dict[str, object] = {
        "base_risk_pct": Decimal("1"),
        "max_risk_pct": Decimal("1.5"),
        "max_notional": Decimal("100000"),
        "max_leverage": Decimal("3"),
        "max_margin": Decimal("50000"),
        "min_stop_distance_pct": Decimal("0.25"),
        "max_stop_distance_pct": Decimal("10"),
    }
    values.update(changes)
    return SingleTradeRiskPolicy.model_validate(values)


def test_stop_based_size_is_approved() -> None:
    decision = SingleTradeRiskEngine().evaluate(request(), policy())
    assert decision.decision == RiskDecisionOutcome.APPROVED
    assert decision.position_size == Decimal("500")
    assert decision.approved_risk_pct == Decimal("1.00000000")


def test_notional_cap_reduces_size() -> None:
    decision = SingleTradeRiskEngine().evaluate(request(), policy(max_notional="10000"))
    assert decision.decision == RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
    assert decision.position_size == Decimal("100")
    assert decision.approved_risk_pct == Decimal("0.20000000")
    assert "trade notional" in decision.reasons[1]


def test_margin_cap_reduces_size() -> None:
    decision = SingleTradeRiskEngine().evaluate(
        request(available_margin="1000"), policy(max_margin="1000")
    )
    assert decision.decision == RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
    assert decision.position_size == Decimal("30")


def test_requested_risk_is_capped() -> None:
    decision = SingleTradeRiskEngine().evaluate(request(requested_risk_pct="2"), policy())
    assert decision.decision == RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
    assert decision.position_size == Decimal("500")
    assert decision.approved_risk_pct == Decimal("1.00000000")


@pytest.mark.parametrize(
    ("request_changes", "policy_changes", "reason"),
    [
        ({"stop_price": "100"}, {}, "equals entry"),
        ({"stop_price": "99.9"}, {}, "below the minimum"),
        ({"stop_price": "80"}, {}, "exceeds the maximum"),
        ({"available_margin": "0"}, {}, "below one lot"),
        ({}, {"base_risk_pct": "2", "max_risk_pct": "1"}, "inconsistent"),
    ],
)
def test_invalid_or_uncapitalized_trade_is_rejected(
    request_changes: dict[str, object],
    policy_changes: dict[str, object],
    reason: str,
) -> None:
    decision = SingleTradeRiskEngine().evaluate(
        request(**request_changes), policy(**policy_changes)
    )
    assert decision.decision == RiskDecisionOutcome.REJECTED
    assert decision.position_size == 0
    assert reason in decision.reasons[0]


def test_contract_multiplier_and_lot_size_are_applied() -> None:
    decision = SingleTradeRiskEngine().evaluate(
        request(contract_multiplier="10", lot_size="0.25"), policy()
    )
    assert decision.position_size == Decimal("50.0")


def test_instrument_leverage_is_more_restrictive() -> None:
    decision = SingleTradeRiskEngine().evaluate(
        request(stop_price="99.9", instrument_max_leverage="1", available_margin="100000"),
        policy(min_stop_distance_pct="0.01", max_margin="100000", max_notional="1000000"),
    )
    assert decision.decision == RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
    assert decision.position_size == Decimal("1000")
    assert decision.limits["leverage"] == Decimal("1")
