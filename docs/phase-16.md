# Phase 16 — First Venue Sandbox Connector

## Objective

Provide exactly one venue boundary for balances, order placement/cancellation/readback, positions, retries, and rate-limit handling.

## Scope

The deterministic sandbox adapter exposes the common venue contract and explicit outage/rate-limit failures. It has no withdrawal capability and sends no production orders. Migration `20260825_0017` provides the connector-operation audit ledger.

## Deferred

Phase 17 composes the complete paper workflow.
