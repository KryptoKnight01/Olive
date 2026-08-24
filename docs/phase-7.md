# Phase 7 — Correlation-Aware Risk

## Objective

Prevent several individually valid trades from creating excessive risk through highly correlated instruments.

## Method

- Calculate Pearson correlations from rolling price returns, never raw prices.
- Use a configured lookback, minimum history, and absolute-correlation threshold.
- Build deterministic connected-component clusters with stable instrument ordering.
- Limit unique open instruments and aggregate stop risk in the proposed trade's cluster.
- Reduce size when cluster risk capacity remains; reject when capacity or position count is exhausted.
- Persist the complete correlation matrix slice, cluster, limits, and decision evidence.

## Trust boundary

Price histories and open positions are authoritative internal data. TradingView cannot supply correlation values, cluster membership, or policy limits.

## Deferred

Covariance, factor, and stressed-correlation models remain future enhancements. Phase 8 introduces bounded dynamic risk multipliers.
