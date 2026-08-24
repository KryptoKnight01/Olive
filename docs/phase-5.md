# Phase 5 — Portfolio Risk Engine V1

## Objective

Evaluate every Phase 4-sized trade against the projected post-trade portfolio before order creation.

## Implemented controls

- Gross, net, long, and short exposure limits.
- Open stop-risk limit.
- Margin-utilization and leverage limits.
- Maximum concurrent-position limit.
- Proportional size reduction when capacity remains below the requested size.
- Rejection when no safe capacity remains.
- Immutable current-state, projected-state, limit, outcome, and reason evidence.

## Trust boundary

Open positions and equity are authoritative internal snapshots. TradingView signals cannot supply or override portfolio state or policy limits.

## Decision flow

1. Phase 4 determines the maximum single-trade size.
2. Phase 5 aggregates authoritative open positions.
3. The engine projects the proposed trade into every portfolio metric.
4. The most restrictive remaining capacity determines the approved fraction.
5. The decision and all evidence are persisted before order workflow begins.

## Outcomes

- `APPROVED`: the complete proposed trade fits all limits.
- `APPROVED_WITH_REDUCED_SIZE`: only a safe fraction fits.
- `REJECTED`: no capacity remains or the concurrent-position limit is reached.

## Deferred

Correlation clusters, dynamic regime/drawdown/liquidity multipliers, execution, reconciliation, and authenticated administration remain in later phases.
