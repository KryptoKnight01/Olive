from decimal import Decimal
from uuid import uuid4

import pytest

from olive.risk.protection import LossProtectionEngine
from olive.risk.schemas import LossProtectionInput, LossProtectionPolicy, ProtectionAction


def policy(**changes: object) -> LossProtectionPolicy:
    values: dict[str, object] = {
        "max_daily_loss_pct": "2",
        "max_weekly_loss_pct": "5",
        "max_monthly_loss_pct": "10",
        "portfolio_drawdown_throttle_pct": "5",
        "portfolio_drawdown_halt_pct": "10",
        "strategy_drawdown_throttle_pct": "7",
        "strategy_drawdown_halt_pct": "12",
        "consecutive_loss_throttle": 3,
        "consecutive_loss_halt": 5,
        "throttled_multiplier": "0.5",
        "profit_giveback_trigger_pct": "50",
        "minimum_profit_for_giveback": "1000",
        "profit_giveback_multiplier": "0.25",
    }
    values.update(changes)
    return LossProtectionPolicy.model_validate(values)


def request(**changes: object) -> LossProtectionInput:
    values: dict[str, object] = {
        "signal_id": uuid4(),
        "equity": "100000",
        "peak_equity": "100000",
        "strategy_equity": "50000",
        "strategy_peak_equity": "50000",
        "daily_pnl": "0",
        "weekly_pnl": "0",
        "monthly_pnl": "0",
        "peak_daily_pnl": "0",
        "consecutive_losses": 0,
    }
    values.update(changes)
    return LossProtectionInput.model_validate(values)


def test_normal_state_allows_full_risk() -> None:
    decision = LossProtectionEngine().evaluate(request(), policy())
    assert decision.action is ProtectionAction.ALLOW
    assert decision.protection_multiplier == 1


@pytest.mark.parametrize(
    "change",
    [{"daily_pnl": "-2000"}, {"weekly_pnl": "-5000"}, {"monthly_pnl": "-10000"}],
)
def test_period_loss_limits_halt_new_risk(change: dict[str, str]) -> None:
    decision = LossProtectionEngine().evaluate(request(**change), policy())
    assert decision.action is ProtectionAction.HALT_NEW_RISK
    assert decision.protection_multiplier == 0


def test_portfolio_drawdown_throttles_then_halts() -> None:
    throttled = LossProtectionEngine().evaluate(request(equity="94000"), policy())
    halted = LossProtectionEngine().evaluate(request(equity="90000"), policy())
    assert throttled.protection_multiplier == Decimal("0.5")
    assert halted.action is ProtectionAction.HALT_NEW_RISK


def test_consecutive_losses_apply_most_restrictive_control() -> None:
    decision = LossProtectionEngine().evaluate(
        request(equity="94000", consecutive_losses=5), policy()
    )
    assert decision.protection_multiplier == 0
    assert "consecutive losses" in decision.binding_controls


def test_profit_giveback_locks_in_gains() -> None:
    decision = LossProtectionEngine().evaluate(
        request(daily_pnl="1000", peak_daily_pnl="2500"), policy()
    )
    assert decision.action is ProtectionAction.THROTTLE
    assert decision.protection_multiplier == Decimal("0.25")
    assert decision.metrics["profit_giveback_pct"] == Decimal("60.0")


def test_inconsistent_policy_fails_closed() -> None:
    with pytest.raises(ValueError, match="internally inconsistent"):
        LossProtectionEngine().evaluate(
            request(), policy(portfolio_drawdown_throttle_pct="10")
        )
