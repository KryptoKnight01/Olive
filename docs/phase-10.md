# Phase 10 — Portfolio Regime Engine

## Objective

Classify portfolio conditions using transparent measurements and apply regime-specific risk, leverage, and new-position controls.

## Regimes

`CALM`, `NORMAL`, `ELEVATED`, `HIGH_VOLATILITY`, and `CRISIS`.

## Inputs

Realized volatility, average absolute correlation, portfolio drawdown, liquidity stress, and market stress. Each input has versioned calm, elevated, high-volatility, and crisis thresholds.

## Decision method

Each metric is classified independently. The portfolio adopts the highest triggered severity, making the result conservative and deterministic. The decision exposes every metric classification and the binding metrics.

## Controls

Each regime defines a risk multiplier, maximum leverage, and maximum new positions. Crisis may set all three to zero without automatically liquidating existing positions.

## Evidence and trust

The ledger preserves inputs, metric classifications, regime, controls, reasons, observation ID, and policy version. Inputs originate from authoritative Olive services; TradingView cannot declare the portfolio regime.

## Deferred

Phase 11 introduces normalized market data, timestamps, stale-data detection, and price sanity checks.
