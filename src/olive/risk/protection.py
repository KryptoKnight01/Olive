from __future__ import annotations

from decimal import Decimal

from olive.risk.schemas import (
    LossProtectionDecision,
    LossProtectionInput,
    LossProtectionPolicy,
    ProtectionAction,
)

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


class LossProtectionEngine:
    """Apply hard loss limits and deterministic drawdown/profit throttles."""

    def evaluate(
        self, request: LossProtectionInput, policy: LossProtectionPolicy
    ) -> LossProtectionDecision:
        self._validate(policy)
        portfolio_drawdown = max(
            ZERO,
            (request.peak_equity - request.equity) / request.peak_equity * HUNDRED,
        )
        strategy_drawdown = max(
            ZERO,
            (request.strategy_peak_equity - request.strategy_equity)
            / request.strategy_peak_equity
            * HUNDRED,
        )
        losses = {
            "daily loss": max(ZERO, -request.daily_pnl / request.peak_equity * HUNDRED),
            "weekly loss": max(ZERO, -request.weekly_pnl / request.peak_equity * HUNDRED),
            "monthly loss": max(ZERO, -request.monthly_pnl / request.peak_equity * HUNDRED),
        }
        candidates: list[tuple[str, Decimal]] = []
        for name, value, maximum in (
            ("daily loss", losses["daily loss"], policy.max_daily_loss_pct),
            ("weekly loss", losses["weekly loss"], policy.max_weekly_loss_pct),
            ("monthly loss", losses["monthly loss"], policy.max_monthly_loss_pct),
        ):
            if value >= maximum:
                candidates.append((name, ZERO))
        candidates.append(
            (
                "portfolio drawdown",
                self._drawdown_multiplier(
                    portfolio_drawdown,
                    policy.portfolio_drawdown_throttle_pct,
                    policy.portfolio_drawdown_halt_pct,
                    policy.throttled_multiplier,
                ),
            ),
        )
        candidates.append(
            (
                "strategy drawdown",
                self._drawdown_multiplier(
                    strategy_drawdown,
                    policy.strategy_drawdown_throttle_pct,
                    policy.strategy_drawdown_halt_pct,
                    policy.throttled_multiplier,
                ),
            ),
        )
        streak_multiplier = ONE
        if request.consecutive_losses >= policy.consecutive_loss_halt:
            streak_multiplier = ZERO
        elif request.consecutive_losses >= policy.consecutive_loss_throttle:
            streak_multiplier = policy.throttled_multiplier
        candidates.append(("consecutive losses", streak_multiplier))

        giveback_pct = ZERO
        if request.peak_daily_pnl >= policy.minimum_profit_for_giveback:
            giveback_pct = max(
                ZERO,
                (request.peak_daily_pnl - request.daily_pnl)
                / request.peak_daily_pnl
                * HUNDRED,
            )
            if giveback_pct >= policy.profit_giveback_trigger_pct:
                candidates.append(("profit giveback", policy.profit_giveback_multiplier))
        multiplier = min((value for _, value in candidates), default=ONE)
        binding = [name for name, value in candidates if value == multiplier and value < ONE]
        action = (
            ProtectionAction.HALT_NEW_RISK
            if multiplier == ZERO
            else ProtectionAction.ALLOW
            if multiplier == ONE
            else ProtectionAction.THROTTLE
        )
        return LossProtectionDecision(
            signal_id=request.signal_id,
            action=action,
            protection_multiplier=multiplier,
            metrics={
                **losses,
                "portfolio_drawdown_pct": portfolio_drawdown,
                "strategy_drawdown_pct": strategy_drawdown,
                "profit_giveback_pct": giveback_pct,
                "consecutive_losses": request.consecutive_losses,
            },
            thresholds=self._thresholds(policy),
            binding_controls=binding,
            reasons=["most restrictive active protection control applied"],
        )

    @staticmethod
    def _drawdown_multiplier(
        drawdown: Decimal, throttle: Decimal, halt: Decimal, multiplier: Decimal
    ) -> Decimal:
        if drawdown >= halt:
            return ZERO
        if drawdown >= throttle:
            return multiplier
        return ONE

    @staticmethod
    def _validate(policy: LossProtectionPolicy) -> None:
        if policy.portfolio_drawdown_throttle_pct >= policy.portfolio_drawdown_halt_pct:
            raise ValueError("portfolio drawdown policy is internally inconsistent")
        if policy.strategy_drawdown_throttle_pct >= policy.strategy_drawdown_halt_pct:
            raise ValueError("strategy drawdown policy is internally inconsistent")
        if policy.consecutive_loss_throttle >= policy.consecutive_loss_halt:
            raise ValueError("consecutive-loss policy is internally inconsistent")

    @staticmethod
    def _thresholds(policy: LossProtectionPolicy) -> dict[str, Decimal | int]:
        return {
            "max_daily_loss_pct": policy.max_daily_loss_pct,
            "max_weekly_loss_pct": policy.max_weekly_loss_pct,
            "max_monthly_loss_pct": policy.max_monthly_loss_pct,
            "portfolio_drawdown_throttle_pct": policy.portfolio_drawdown_throttle_pct,
            "portfolio_drawdown_halt_pct": policy.portfolio_drawdown_halt_pct,
            "strategy_drawdown_throttle_pct": policy.strategy_drawdown_throttle_pct,
            "strategy_drawdown_halt_pct": policy.strategy_drawdown_halt_pct,
            "consecutive_loss_throttle": policy.consecutive_loss_throttle,
            "consecutive_loss_halt": policy.consecutive_loss_halt,
            "profit_giveback_trigger_pct": policy.profit_giveback_trigger_pct,
        }
