# Phase 14 — Position Protection Engine

## Objective

Detect unprotected positions, incorrect protection quantities, and orphan reduce-only orders.

## Contract

Every non-flat position requires stop coverage equal to the open quantity and target coverage no greater than that quantity. Missing or mismatched protection is critical and blocks safe pipeline continuation. Migration `20260825_0015` preserves assessments and reasons.

## Deferred

Phase 15 compares Olive state with venue state continuously.
