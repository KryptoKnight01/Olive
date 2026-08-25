# Phase 12 — Liquidity and Execution Risk

## Objective

Prevent otherwise valid trades from entering the market at unsafe size, spread, slippage, or participation levels.

## Scope

- Enforce maximum spread and expected-slippage thresholds.
- Calculate executable capacity from both average daily volume and available order-book notional.
- Apply the most restrictive capacity.
- Produce deterministic `APPROVE`, `REDUCE`, `SPLIT`, `DEFER`, or `REJECT` actions.
- Persist requested and approved quantities/notionals, slice count, binding limits, and reasons.
- Reject non-valid authoritative market data before liquidity evaluation.

## Decision behavior

Temporary spread or slippage breaches defer execution. Orders within capacity are approved. Orders moderately above capacity are reduced. Larger orders may be split when the required slice count remains within policy. Missing capacity, sub-minimum executable size, invalid market data, or excessive slicing rejects the order.

## Database changes

Migration `20260825_0013` adds versioned execution-risk policies and an immutable decision ledger linked to the normalized market quote used in the calculation.

## Automated tests

Tests cover approval, spread deferral, slippage deferral, invalid data rejection, size reduction, order splitting, excessive-slice rejection, and minimum-capacity rejection.

## Security and risk

TradingView cannot provide authoritative liquidity approval. All calculations use Decimal arithmetic and return explicit limits and reasons. A deferred decision is not an approval and may only be reevaluated with a fresh quote.

## Known limitations

Expected slippage and available-book notional are supplied observations in this phase. Venue-specific order-book adapters and realized execution-quality calibration are deferred.

## Deferred

Phase 13 introduces the paper order management system, including orders, fills, positions, fees, partial fills, cancellations, stops, targets, and PnL simulation.
