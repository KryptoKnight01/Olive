from decimal import Decimal
from uuid import uuid4

from olive.risk.correlation import CorrelationRiskEngine
from olive.risk.schemas import (
    CorrelatedPosition,
    CorrelationRiskInput,
    CorrelationRiskPolicy,
    RiskDecisionOutcome,
)


def policy(**changes: object) -> CorrelationRiskPolicy:
    values: dict[str, object] = {
        "lookback_observations": 6,
        "minimum_observations": 5,
        "cluster_threshold": "0.8",
        "max_correlated_positions": 2,
        "max_cluster_stop_risk": "3000",
    }
    values.update(changes)
    return CorrelationRiskPolicy.model_validate(values)


def request(*positions: CorrelatedPosition, **changes: object) -> CorrelationRiskInput:
    values: dict[str, object] = {
        "signal_id": uuid4(),
        "proposed_instrument_key": "BTC",
        "proposed_notional": "50000",
        "proposed_stop_risk": "1000",
        "price_history": {
            "BTC": ["100", "101", "103", "102", "104", "107"],
            "ETH": ["200", "202", "206", "204", "208", "214"],
            "WBTC": ["50", "50.5", "51.5", "51", "52", "53.5"],
            "CASH": ["1", "1", "1", "1", "1", "1"],
        },
        "positions": positions,
    }
    values.update(changes)
    return CorrelationRiskInput.model_validate(values)


def position(instrument: str, risk: str = "1000") -> CorrelatedPosition:
    return CorrelatedPosition(instrument_key=instrument, open_stop_risk=Decimal(risk))


def test_rolling_return_correlation_builds_deterministic_cluster() -> None:
    decision = CorrelationRiskEngine().evaluate(request(), policy())

    assert decision.decision is RiskDecisionOutcome.APPROVED
    assert decision.proposed_cluster == ("BTC", "ETH", "WBTC")
    assert decision.correlations["BTC|ETH"] == Decimal("1")
    assert decision.current_cluster_positions == 0


def test_cluster_position_limit_rejects_new_position() -> None:
    decision = CorrelationRiskEngine().evaluate(
        request(position("ETH"), position("WBTC")), policy(max_correlated_positions=2)
    )

    assert decision.decision is RiskDecisionOutcome.REJECTED
    assert decision.reasons == ["maximum correlated positions reached"]


def test_adding_to_existing_instrument_does_not_increase_position_count() -> None:
    decision = CorrelationRiskEngine().evaluate(
        request(position("BTC"), position("ETH")),
        policy(max_correlated_positions=2, max_cluster_stop_risk="5000"),
    )

    assert decision.decision is RiskDecisionOutcome.APPROVED


def test_cluster_stop_risk_reduces_trade() -> None:
    decision = CorrelationRiskEngine().evaluate(
        request(position("ETH", "2500")), policy(max_cluster_stop_risk="3000")
    )

    assert decision.decision is RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
    assert decision.approved_fraction == Decimal("0.5")
    assert decision.approved_notional == Decimal("25000.0")
    assert decision.projected_cluster_stop_risk == Decimal("3000.0")


def test_insufficient_history_rejects_deterministically() -> None:
    decision = CorrelationRiskEngine().evaluate(
        request(price_history={"BTC": ["1", "2"]}), policy()
    )

    assert decision.decision is RiskDecisionOutcome.REJECTED
    assert decision.reasons == ["proposed instrument has insufficient history"]
