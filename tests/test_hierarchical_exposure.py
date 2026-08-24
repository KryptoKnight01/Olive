from decimal import Decimal
from uuid import uuid4

from olive.risk.hierarchy import HierarchicalExposureEngine
from olive.risk.schemas import (
    ExposurePosition,
    HierarchicalExposureLimit,
    HierarchicalRiskInput,
    RiskDecisionOutcome,
)


def limit(dimension: str, key: str, metric: str, maximum: str) -> HierarchicalExposureLimit:
    return HierarchicalExposureLimit.model_validate(
        {"dimension": dimension, "scope_key": key, "metric": metric, "maximum": maximum}
    )


def position(notional: str, *, theme: tuple[str, ...] = ("CRYPTO_BETA",)) -> ExposurePosition:
    return ExposurePosition.model_validate(
        {
            "tags": {
                "INSTRUMENT": ["BTC-USD"],
                "UNDERLYING": ["BTC"],
                "STRATEGY": ["OLC"],
                "ASSET_CLASS": ["CRYPTO"],
                "THEME": list(theme),
                "VENUE": ["COINBASE"],
                "ACCOUNT": ["PAPER-1"],
                "PORTFOLIO": ["DEFAULT"],
            },
            "gross_notional": notional,
            "open_stop_risk": "1000",
            "margin_used": "10000",
        }
    )


def request(*positions: ExposurePosition) -> HierarchicalRiskInput:
    return HierarchicalRiskInput.model_validate(
        {
            "signal_id": uuid4(),
            "proposed_tags": position("0").tags,
            "proposed_notional": "50000",
            "proposed_stop_risk": "1000",
            "proposed_margin": "10000",
            "positions": positions,
        }
    )


def test_most_restrictive_matching_limit_reduces_size() -> None:
    limits = (
        limit("PORTFOLIO", "DEFAULT", "GROSS_NOTIONAL", "500000"),
        limit("ASSET_CLASS", "CRYPTO", "GROSS_NOTIONAL", "200000"),
        limit("UNDERLYING", "BTC", "GROSS_NOTIONAL", "120000"),
    )
    decision = HierarchicalExposureEngine().evaluate(request(position("100000")), limits)

    assert decision.decision is RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
    assert decision.approved_fraction == Decimal("0.4")
    assert decision.approved_notional == Decimal("20000.0")
    assert decision.binding_limit == "UNDERLYING:BTC:GROSS_NOTIONAL"
    assert len(decision.evaluations) == 3


def test_unmatched_limits_do_not_apply() -> None:
    limits = (limit("SECTOR", "TECHNOLOGY", "GROSS_NOTIONAL", "1"),)
    decision = HierarchicalExposureEngine().evaluate(request(), limits)

    assert decision.decision is RiskDecisionOutcome.APPROVED
    assert decision.binding_limit is None


def test_multi_value_theme_membership_is_aggregated() -> None:
    tagged = position("25000", theme=("CRYPTO_BETA", "AI"))
    limits = (limit("THEME", "AI", "GROSS_NOTIONAL", "50000"),)
    proposed = request(tagged).model_copy(update={"proposed_tags": tagged.tags})
    decision = HierarchicalExposureEngine().evaluate(proposed, limits)

    assert decision.approved_fraction == Decimal("0.5")


def test_open_risk_limit_can_override_notional_limit() -> None:
    limits = (
        limit("STRATEGY", "OLC", "GROSS_NOTIONAL", "1000000"),
        limit("STRATEGY", "OLC", "OPEN_STOP_RISK", "1000"),
    )
    decision = HierarchicalExposureEngine().evaluate(request(), limits)

    assert decision.approved_fraction == Decimal("1")
    decision = HierarchicalExposureEngine().evaluate(request(position("10000")), limits)
    assert decision.decision is RiskDecisionOutcome.REJECTED
    assert decision.binding_limit == "STRATEGY:OLC:OPEN_STOP_RISK"


def test_position_count_limit_rejects_when_full() -> None:
    limits = (limit("ACCOUNT", "PAPER-1", "POSITION_COUNT", "1"),)
    decision = HierarchicalExposureEngine().evaluate(request(position("1000")), limits)

    assert decision.decision is RiskDecisionOutcome.REJECTED
