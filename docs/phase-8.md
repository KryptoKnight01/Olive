# Phase 8 — Dynamic Risk Multipliers

## Objective

Adjust base trade risk using bounded, explainable state multipliers while preserving every absolute risk cap.

## Components

Regime, correlation, drawdown, liquidity, signal quality, strategy health, and event risk.

## Calculation

`Final Risk = MIN(Base Risk × bounded multiplier product, Base Risk, Hard Maximum Risk)`

The base risk is a ceiling, not an entitlement. Favorable inputs cannot override it. Each component has configuration-versioned minimum and maximum bounds.

## Evidence

The ledger stores raw inputs, bounded inputs, the multiplier product, uncapped result, base and hard caps, final risk, policy version, and reasons.

## Trust boundary

Multipliers are supplied by authoritative internal services. TradingView metadata cannot set final multipliers or bypass their bounds.

## Deferred

Phase 9 implements drawdown, loss, and profit-protection state. Phase 10 implements the portfolio regime engine that will produce authoritative regime inputs.
