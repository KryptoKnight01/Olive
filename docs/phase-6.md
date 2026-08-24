# Phase 6 — Hierarchical Exposure Limits

## Objective

Apply configuration-driven exposure controls at every required hierarchy level and make the most restrictive matching limit authoritative.

## Supported dimensions

Instrument, underlying, strategy, asset class, sector, industry, theme, venue, account, and portfolio.

## Supported controls

Gross notional, open stop risk, margin used, and position count. Each proposed trade may carry multiple values for a dimension, including several themes.

## Decision method

1. Match enabled, versioned limits against the proposed trade's canonical tags.
2. Aggregate only existing positions sharing the limit's dimension and scope key.
3. Calculate remaining capacity and the safe fraction of the proposal.
4. Select the smallest safe fraction across every matched limit.
5. Persist all evaluations, the binding limit, configuration version, and outcome.

## Outcomes

- `APPROVED`: the proposal fits every matching limit.
- `APPROVED_WITH_REDUCED_SIZE`: the tightest limit permits a smaller trade.
- `REJECTED`: at least one applicable scope has no remaining capacity.

## Trust boundary

Canonical classification tags and open positions come from Olive's internal domain and portfolio state. TradingView cannot set limit scopes, values, or exposure snapshots.

## Deferred

Correlation clusters and rolling correlations begin in Phase 7. Dynamic risk multipliers begin in Phase 8.
