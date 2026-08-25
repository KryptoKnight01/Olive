# Phase 13 — Paper Order Management System

## Objective

Simulate orders, fills, positions, fees, and PnL without sending real orders.

## Scope and behavior

The OMS supports idempotent client order IDs, market/limit/stop/target order contracts, partial and complete fills, cancellations, reduce-only enforcement, weighted average fills, position updates, fees, and realized PnL. Invalid overfills and unsafe reduce-only orders fail explicitly.

## Persistence and tests

Migration `20260825_0014` creates paper order, fill, and position ledgers. Tests cover partial fills, completion, idempotency, reduce-only safety, fees, and position accounting.

## Deferred

Phase 14 verifies that every open paper position has correct protection.
