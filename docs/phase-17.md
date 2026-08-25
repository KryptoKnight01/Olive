# Phase 17 — End-to-End Paper Pipeline

## Objective

Complete the TradingView-to-analytics paper milestone without real capital.

## Pipeline

The accepted upstream decision enters the paper venue, fills, creates a position, verifies stop/target protection, reconciles orders/positions/balance, exits reduce-only, and calculates fee-adjusted realized PnL. Any protection or reconciliation failure stops the workflow. Migration `20260825_0018` stores pipeline outcomes.

## Acceptance

All unit/static checks, migrations, schema-drift detection, health checks, and the complete Phase 2-17 Docker smoke chain must pass. The reference round trip buys two units at 100, sells at 110, and records 19.58 after fees.

## Known limitations

The sandbox is deterministic and not yet an external exchange API. Advanced order types, latency models, and live credentials remain out of scope.

## Deferred

Phase 18 introduces Admin Web Application V1.
