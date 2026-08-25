from decimal import Decimal

from olive.production.engine import ControlledProductionEngine
from olive.production.schemas import (
    AssetProductionPolicy,
    ExecutionObservation,
    LiveCapitalPolicy,
    LiveOrderRequest,
    ProductionMode,
    StrategySignal,
    VenueExposure,
    VenueQuote,
)


def live_policy(**changes: object) -> LiveCapitalPolicy:
    values: dict[str, object] = {
        "mode": ProductionMode.LIMITED_LIVE,
        "approved_strategy": "olive",
        "approved_instruments": frozenset({"BTCUSDT"}),
        "approved_venue": "venue-a",
        "max_order_notional": Decimal("1000"),
        "max_total_exposure": Decimal("5000"),
        "max_leverage": Decimal("1.5"),
        "readiness_approved": True,
        "operator_armed": True,
    }
    values.update(changes)
    return LiveCapitalPolicy.model_validate(values)


def order(**changes: object) -> LiveOrderRequest:
    values: dict[str, object] = {
        "signal_id": "sig-1",
        "strategy_key": "olive",
        "instrument": "BTCUSDT",
        "venue": "venue-a",
        "requested_notional": Decimal("500"),
        "projected_total_exposure": Decimal("2000"),
        "projected_leverage": Decimal("1"),
    }
    values.update(changes)
    return LiveOrderRequest.model_validate(values)


def test_live_capital_is_disarmed_by_default() -> None:
    decision = ControlledProductionEngine().authorize_live_order(
        order(), live_policy(mode=ProductionMode.DISARMED, operator_armed=False)
    )
    assert decision.route_permitted is False
    assert decision.approved_notional == 0
    assert "LIVE_MODE_DISARMED" in decision.reasons


def test_limited_live_reduces_order_to_hard_cap() -> None:
    decision = ControlledProductionEngine().authorize_live_order(
        order(requested_notional=Decimal("1500")), live_policy()
    )
    assert decision.route_permitted is True
    assert decision.approved_notional == Decimal("1000")
    assert decision.reasons == ("ORDER_NOTIONAL_REDUCED",)


def test_unapproved_instrument_cannot_route() -> None:
    decision = ControlledProductionEngine().authorize_live_order(
        order(instrument="ETHUSDT"), live_policy()
    )
    assert decision.route_permitted is False
    assert "INSTRUMENT_NOT_APPROVED" in decision.reasons


def test_live_paper_deviation_detects_slippage_and_pnl() -> None:
    report = ControlledProductionEngine().analyze_deviation(
        ExecutionObservation(
            signal_id="sig-1",
            paper_delay_ms=100,
            live_delay_ms=600,
            paper_fill_price=Decimal("100"),
            live_fill_price=Decimal("102"),
            paper_fee=Decimal("1"),
            live_fee=Decimal("1.5"),
            paper_pnl=Decimal("10"),
            live_pnl=Decimal("5"),
        ),
        200,
        Decimal("1"),
        Decimal("2"),
    )
    assert report.breached is True
    assert report.slippage_pct == Decimal("2.0000")
    assert set(report.reasons) == {"DELAY_DEVIATION", "SLIPPAGE_DEVIATION", "PNL_DIVERGENCE"}


def test_live_paper_deviation_detects_missed_fill() -> None:
    report = ControlledProductionEngine().analyze_deviation(
        ExecutionObservation(
            signal_id="sig-2",
            paper_delay_ms=100,
            live_delay_ms=100,
            paper_fill_price=Decimal("100"),
            live_fill_price=None,
            paper_fee=Decimal("1"),
            live_fee=Decimal("0"),
            paper_pnl=Decimal("0"),
            live_pnl=Decimal("0"),
        ),
        200,
        Decimal("1"),
        Decimal("2"),
    )
    assert report.missed_fill is True
    assert report.slippage_pct is None


def test_multi_venue_selects_best_healthy_effective_price() -> None:
    selection = ControlledProductionEngine().select_venue(
        [
            VenueQuote(
                venue="a",
                price=Decimal("100"),
                available_notional=Decimal("1000"),
                fee_pct=Decimal("0.2"),
            ),
            VenueQuote(
                venue="b",
                price=Decimal("99.9"),
                available_notional=Decimal("800"),
                fee_pct=Decimal("0.05"),
            ),
            VenueQuote(
                venue="c",
                price=Decimal("90"),
                available_notional=Decimal("1000"),
                fee_pct=Decimal("0"),
                healthy=False,
            ),
        ],
        Decimal("1000"),
        "BUY",
    )
    assert selection.venue == "b"
    assert selection.approved_notional == Decimal("800")


def test_exposure_is_consolidated_across_venues() -> None:
    total = ControlledProductionEngine().consolidated_exposure(
        [
            VenueExposure(venue="a", gross_exposure=Decimal("2000")),
            VenueExposure(venue="b", gross_exposure=Decimal("3000")),
        ]
    )
    assert total == Decimal("5000")


def test_portfolio_authority_resolves_conflicts_and_budget() -> None:
    result = ControlledProductionEngine().resolve_strategies(
        [
            StrategySignal(
                strategy_key="primary",
                instrument="BTCUSDT",
                direction=1,
                priority=100,
                requested_risk_pct=Decimal("0.8"),
            ),
            StrategySignal(
                strategy_key="secondary",
                instrument="BTCUSDT",
                direction=1,
                priority=50,
                requested_risk_pct=Decimal("0.7"),
            ),
            StrategySignal(
                strategy_key="opposite",
                instrument="BTCUSDT",
                direction=-1,
                priority=20,
                requested_risk_pct=Decimal("0.5"),
            ),
        ],
        Decimal("1"),
    )
    assert result.direction == 1
    assert result.total_risk_pct == Decimal("1")
    assert result.allocations[1].approved_risk_pct == Decimal("0.2")
    assert result.allocations[2].reason == "DIRECTION_CONFLICT"


def test_asset_class_must_be_explicitly_enabled() -> None:
    policy = AssetProductionPolicy(
        asset_class="EQUITY",
        approved_instruments=frozenset({"AAPL"}),
        approved_venues=frozenset({"broker"}),
        max_notional=Decimal("1000"),
        enabled=False,
    )
    result = ControlledProductionEngine().check_asset_eligibility(
        "AAPL", "broker", Decimal("500"), policy
    )
    assert result.eligible is False
    assert result.reasons == ("ASSET_CLASS_DISABLED",)


def test_enabled_asset_is_still_capped() -> None:
    policy = AssetProductionPolicy(
        asset_class="CRYPTO",
        approved_instruments=frozenset({"BTCUSDT"}),
        approved_venues=frozenset({"venue-a"}),
        max_notional=Decimal("1000"),
        enabled=True,
    )
    result = ControlledProductionEngine().check_asset_eligibility(
        "BTCUSDT", "venue-a", Decimal("1500"), policy
    )
    assert result.eligible is True
    assert result.approved_notional == Decimal("1000")
