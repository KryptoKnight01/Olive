# Phase 15 — Reconciliation Engine

## Objective

Compare internal orders, positions, and balances with the venue snapshot.

## Contract

Any missing, unexpected, or quantity-different order or position and any balance difference is reported explicitly. Critical mismatch sets `suspend_entries=true`. Migration `20260825_0016` stores every reconciliation outcome.

## Deferred

Phase 16 supplies the first real connector boundary.
