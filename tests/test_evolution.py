from decimal import Decimal

import pytest

from olive.evolution.engine import EvolutionEngine
from olive.evolution.schemas import (
    AuthorityPolicy,
    CapitalPool,
    ExecutionRequest,
    ExecutionStyle,
    PortfolioAnalyticsInput,
    SignalAuthority,
    StrategyBar,
)


def test_capital_pool_caps_allocation_and_calculates_units() -> None:
    result = EvolutionEngine().allocate_pool(
        CapitalPool(
            pool_key="p",
            allocated_capital=Decimal("10000"),
            reserved_capital=Decimal("2000"),
            investor_units=Decimal("100"),
        ),
        Decimal("9000"),
    )
    assert result.approved_notional == Decimal("8000") and result.unit_value == Decimal("100")


def test_twap_preserves_total_quantity() -> None:
    result = EvolutionEngine().build_execution_plan(
        ExecutionRequest(
            order_id="o",
            total_quantity=Decimal("10"),
            duration_minutes=10,
            slices=5,
            reference_price=Decimal("100"),
            max_participation_pct=Decimal("5"),
        ),
        ExecutionStyle.TWAP,
    )
    assert len(result.slices) == 5 and result.total_quantity == Decimal("10.00000000")


def test_vwap_requires_aligned_weights() -> None:
    request = ExecutionRequest(
        order_id="o",
        total_quantity=Decimal("10"),
        duration_minutes=10,
        slices=2,
        reference_price=Decimal("100"),
        max_participation_pct=Decimal("5"),
    )
    with pytest.raises(ValueError, match="one volume weight"):
        EvolutionEngine().build_execution_plan(request, ExecutionStyle.VWAP, (Decimal("1"),))


def test_analytics_returns_var_es_covariance_and_contribution() -> None:
    result = EvolutionEngine().analyze_portfolio(
        PortfolioAnalyticsInput(
            portfolio_value=Decimal("1000"),
            position_values={"BTC": Decimal("600"), "ETH": Decimal("400")},
            returns={
                "BTC": (Decimal("-0.1"), Decimal("0.05"), Decimal("-0.02")),
                "ETH": (Decimal("-0.05"), Decimal("0.02"), Decimal("-0.01")),
            },
        )
    )
    assert result.value_at_risk == Decimal("80.00")
    assert result.expected_shortfall == Decimal("80.00")
    assert result.risk_contribution["BTC"] == Decimal("0.6")
    assert "ETH" in result.covariance["BTC"]


def test_native_strategy_signal_is_deterministic() -> None:
    result = EvolutionEngine().native_signal(
        "OLC",
        StrategyBar(close=Decimal("110"), fast_average=Decimal("105"), slow_average=Decimal("100")),
        "1.0",
    )
    assert result.direction == 1 and result.reason == "PRICE_AND_FAST_ABOVE_SLOW"


def test_parity_requires_aligned_histories() -> None:
    with pytest.raises(ValueError, match="aligned"):
        EvolutionEngine().check_parity([1], [1, 0], Decimal("99"))


def test_parity_threshold_is_enforced() -> None:
    result = EvolutionEngine().check_parity([1, 0, -1, 1], [1, 0, -1, 0], Decimal("80"))
    assert result.parity_pct == Decimal("75.00") and result.passed is False


def test_native_authority_requires_parity_and_review() -> None:
    result = EvolutionEngine().decide_authority(
        AuthorityPolicy(
            authority=SignalAuthority.NATIVE_PYTHON,
            minimum_parity_pct=Decimal("99"),
            observed_parity_pct=Decimal("98"),
            review_approved=False,
        )
    )
    assert result.production_authority_granted is False
    assert result.tradingview_required is True
    assert set(result.reasons) == {"PARITY_THRESHOLD_NOT_MET", "AUTHORITY_REVIEW_NOT_APPROVED"}


def test_approved_native_authority_removes_infrastructure_dependency() -> None:
    result = EvolutionEngine().decide_authority(
        AuthorityPolicy(
            authority=SignalAuthority.NATIVE_PYTHON,
            minimum_parity_pct=Decimal("99"),
            observed_parity_pct=Decimal("100"),
            review_approved=True,
        )
    )
    assert result.production_authority_granted is True and result.tradingview_required is False
