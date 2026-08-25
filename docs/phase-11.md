# Phase 11 — Market Data Service

## Objective

Provide one normalized, timestamped market-data interface and reject unsafe data before it can influence validation, risk, or execution.

## Scope

- Normalize bid, ask, last, volume, and OHLCV data by instrument, venue, and source.
- Preserve source, receipt, bar-open, and bar-close timestamps.
- Calculate mid-price, absolute spread, percentage spread, and observation age.
- Classify quotes as `VALID`, `STALE`, or `INVALID` with deterministic reasons.
- Detect crossed markets, excessive spreads, excessive price jumps, stale observations, and timestamps too far in the future.
- Persist normalized quotes, candles, calculated quality metrics, and reasons.
- Expose quote ingestion, OHLCV ingestion, and latest-quote retrieval endpoints.

## Configuration

Environment-backed settings control maximum quote age, future clock skew, spread percentage, and price-jump percentage. Defaults are conservative development values and must be explicitly reviewed before production use.

## Security and risk

All timestamps must be timezone-aware. Unknown instruments are rejected. Unsafe data remains auditable but is marked non-valid so downstream services can fail closed. Market data supplied by TradingView does not become an authoritative quote merely because it arrived in a signal.

## Database changes

Migration `20260825_0012` adds normalized `market_quotes` and `market_ohlcv` ledgers, indexed by instrument and time and linked to the canonical instrument master.

## Automated tests

Tests cover valid normalization, stale observations, crossed markets, excessive spreads, implausible price jumps, future timestamps, missing timezone information, and inconsistent OHLCV ranges.

## Run and test

Run the standard unit, Ruff, mypy, migration, schema-drift, health, and Docker smoke gates. Phase 11 is accepted only when the full Phase 2–11 Docker chain passes.

## Known limitations

Phase 11 provides a normalized ingestion and quality foundation. It does not yet connect to a live data vendor, arbitrate competing sources, backfill gaps, or implement order-book depth.

## Deferred

Phase 12 uses these normalized observations for liquidity and execution-risk decisions such as approve, reduce, split, defer, or reject.
