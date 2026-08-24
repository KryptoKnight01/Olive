from decimal import Decimal
from uuid import uuid4

import pytest

from olive.risk.portfolio import PortfolioRiskEngine
from olive.risk.schemas import (
    PortfolioPosition,
    PortfolioRiskInput,
    PortfolioRiskPolicy,
    PositionSide,
    RiskDecisionOutcome,
)


def policy(**changes: object) -> PortfolioRiskPolicy:
    values: dict[str, object] = {
        "max_gross_exposure_pct": "300",
        "max_net_exposure_pct": "200",
        "max_long_exposure_pct": "250",
        "max_short_exposure_pct": "150",
        "max_open_stop_risk_pct": "5",
        "max_margin_utilization_pct": "80",
        "max_leverage": "3",
        "max_concurrent_positions": 10,
    }
    values.update(changes)
    return PortfolioRiskPolicy.model_validate(values)


def request(**changes: object) -> PortfolioRiskInput:
    values: dict[str, object] = {
        "signal_id": uuid4(),
        "equity": "100000",
        "proposed_side": "LONG",
        "proposed_notional": "50000",
        "proposed_stop_risk": "1000",
        "proposed_margin": "10000",
        "positions": (),
    }
    values.update(changes)
    return PortfolioRiskInput.model_validate(values)


def position(side: PositionSide, notional: str, stop: str, margin: str) -> PortfolioPosition:
    return PortfolioPosition(side=side, notional=notional, stop_risk=stop, margin_used=margin)  # type: ignore[arg-type]


def test_trade_is_approved_from_projected_state() -> None:
    decision = PortfolioRiskEngine().evaluate(request(), policy())

    assert decision.decision is RiskDecisionOutcome.APPROVED
    assert decision.approved_fraction == 1
    assert decision.projected["gross_exposure"] == Decimal("50000")
    assert decision.projected["net_exposure"] == Decimal("50000")
    assert decision.projected["position_count"] == 1


def test_gross_exposure_reduces_proposed_trade() -> None:
    positions = (position(PositionSide.LONG, "280000", "2000", "30000"),)
    decision = PortfolioRiskEngine().evaluate(
        request(positions=positions),
        policy(max_long_exposure_pct="400", max_net_exposure_pct="400"),
    )

    assert decision.decision is RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
    assert decision.approved_fraction == Decimal("0.4")
    assert decision.approved_notional == Decimal("20000.0")
    assert decision.projected["gross_exposure"] == Decimal("300000.0")


def test_net_limit_accounts_for_long_short_offset() -> None:
    positions = (
        position(PositionSide.LONG, "200000", "1000", "20000"),
        position(PositionSide.SHORT, "100000", "1000", "10000"),
    )
    decision = PortfolioRiskEngine().evaluate(
        request(positions=positions, proposed_notional="150000"),
        policy(max_gross_exposure_pct="500", max_leverage="5", max_long_exposure_pct="400"),
    )

    assert decision.approved_notional == Decimal("100000")
    assert decision.projected["net_exposure"] == Decimal("200000")


def test_short_trade_uses_absolute_net_boundary() -> None:
    positions = (position(PositionSide.SHORT, "180000", "1000", "20000"),)
    decision = PortfolioRiskEngine().evaluate(
        request(positions=positions, proposed_side="SHORT", proposed_notional="50000"),
        policy(max_short_exposure_pct="250"),
    )

    assert decision.approved_notional == Decimal("20000.0")
    assert decision.projected["net_exposure"] == Decimal("-200000.0")


def test_stop_risk_and_margin_are_projected() -> None:
    positions = (position(PositionSide.LONG, "50000", "4500", "70000"),)
    decision = PortfolioRiskEngine().evaluate(request(positions=positions), policy())

    assert decision.approved_fraction == Decimal("0.5")
    assert decision.projected["open_stop_risk"] == Decimal("5000.0")
    assert decision.projected["margin_used"] == Decimal("75000.0")


def test_concurrent_position_limit_rejects_new_trade() -> None:
    positions = tuple(
        position(PositionSide.LONG, "1000", "10", "100") for _ in range(2)
    )
    decision = PortfolioRiskEngine().evaluate(
        request(positions=positions), policy(max_concurrent_positions=2)
    )

    assert decision.decision is RiskDecisionOutcome.REJECTED
    assert decision.approved_notional == 0
    assert decision.projected["position_count"] == 2


@pytest.mark.parametrize(
    ("policy_change", "expected_fraction"),
    [
        ({"max_long_exposure_pct": "25"}, Decimal("0.5")),
        ({"max_leverage": "1"}, Decimal("1")),
        ({"max_margin_utilization_pct": "5"}, Decimal("0.5")),
    ],
)
def test_individual_portfolio_caps_bind(
    policy_change: dict[str, str], expected_fraction: Decimal
) -> None:
    decision = PortfolioRiskEngine().evaluate(request(), policy(**policy_change))
    assert decision.approved_fraction == expected_fraction
