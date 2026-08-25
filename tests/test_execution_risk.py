from __future__ import annotations

import uuid
from decimal import Decimal

from olive.execution_risk.engine import ExecutionRiskEngine
from olive.execution_risk.schemas import (
    ExecutionRiskAction,
    ExecutionRiskInput,
    ExecutionRiskPolicy,
)

POLICY = ExecutionRiskPolicy(
    maximum_spread_pct=Decimal("1"),
    maximum_slippage_pct=Decimal("0.5"),
    maximum_adv_participation_pct=Decimal("2"),
    maximum_book_participation_pct=Decimal("20"),
    minimum_executable_notional=Decimal("100"),
    minimum_reduced_fraction=Decimal("0.5"),
    maximum_slices=5,
)


def request(**changes: object) -> ExecutionRiskInput:
    values: dict[str, object] = {
        "signal_id": uuid.uuid4(),
        "market_quote_id": uuid.uuid4(),
        "requested_quantity": Decimal("10"),
        "requested_notional": Decimal("1000"),
        "spread_pct": Decimal("0.2"),
        "expected_slippage_pct": Decimal("0.1"),
        "average_daily_volume_notional": Decimal("100000"),
        "available_book_notional": Decimal("10000"),
        "market_data_status": "VALID",
    }
    values.update(changes)
    return ExecutionRiskInput.model_validate(values)


def test_approves_order_within_liquidity_capacity() -> None:
    result = ExecutionRiskEngine().evaluate(request(), POLICY)
    assert result.action is ExecutionRiskAction.APPROVE
    assert result.approved_notional == Decimal("1000")


def test_defers_wide_spread() -> None:
    result = ExecutionRiskEngine().evaluate(request(spread_pct=Decimal("1.1")), POLICY)
    assert result.action is ExecutionRiskAction.DEFER


def test_defers_excessive_slippage() -> None:
    result = ExecutionRiskEngine().evaluate(
        request(expected_slippage_pct=Decimal("0.6")), POLICY
    )
    assert result.action is ExecutionRiskAction.DEFER


def test_rejects_non_valid_market_data() -> None:
    result = ExecutionRiskEngine().evaluate(request(market_data_status="STALE"), POLICY)
    assert result.action is ExecutionRiskAction.REJECT


def test_reduces_to_binding_book_capacity() -> None:
    result = ExecutionRiskEngine().evaluate(
        request(requested_notional=Decimal("3000"), available_book_notional=Decimal("10000")),
        POLICY,
    )
    assert result.action is ExecutionRiskAction.REDUCE
    assert result.approved_notional == Decimal("2000")
    assert result.approved_quantity == Decimal("6.666666666666666666666666667")


def test_splits_large_order_within_maximum_slices() -> None:
    result = ExecutionRiskEngine().evaluate(
        request(requested_notional=Decimal("5000"), available_book_notional=Decimal("10000")),
        POLICY,
    )
    assert result.action is ExecutionRiskAction.SPLIT
    assert result.slice_count == 3


def test_rejects_order_requiring_too_many_slices() -> None:
    result = ExecutionRiskEngine().evaluate(
        request(requested_notional=Decimal("12000"), available_book_notional=Decimal("10000")),
        POLICY,
    )
    assert result.action is ExecutionRiskAction.REJECT


def test_rejects_capacity_below_minimum_notional() -> None:
    result = ExecutionRiskEngine().evaluate(
        request(available_book_notional=Decimal("400")), POLICY
    )
    assert result.action is ExecutionRiskAction.REJECT
