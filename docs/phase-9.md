# Phase 9 — Drawdown, Loss, and Profit Protection

## Objective

Throttle or halt new risk when realized performance, drawdown, losing streaks, or profit giveback exceed versioned safety thresholds.

## Controls

- Daily, weekly, and monthly loss limits.
- Portfolio and strategy drawdown throttle/halt thresholds.
- Consecutive-loss throttle/halt thresholds.
- Profit-giveback protection after a configured minimum profit is reached.
- Most-restrictive-active-control-wins decision logic.

## Outcomes

- `ALLOW` produces a protection multiplier of `1`.
- `THROTTLE` produces a configured multiplier between `0` and `1`.
- `HALT_NEW_RISK` produces a multiplier of `0`; it does not automatically liquidate positions.

## Evidence

The ledger preserves authoritative PnL/equity inputs, calculated drawdowns and giveback, all thresholds, binding controls, action, multiplier, reasons, and policy version.

## Integration

The protection multiplier is an authoritative input to the Phase 8 dynamic-risk calculation. Hard protection limits always override favorable multipliers.

## Deferred

Phase 10 introduces the portfolio regime engine. Broader pause and liquidation actions remain part of the later kill-switch framework.
