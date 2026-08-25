# Olive Trading Platform

Phases 23–27 add strategy health monitoring, portfolio stress testing, event-risk controls,
non-routing shadow-live simulation, and a mandatory evidence-based live-readiness review.

Phases 28–32 add disarmed-by-default limited-live authorization, live/paper deviation analysis,
multi-venue exposure consolidation, multi-strategy portfolio arbitration, and allowlisted
multi-asset production controls.

Phases 33–37 add separated capital-pool accounting, sliced execution plans, advanced portfolio
analytics, a deterministic native strategy engine, and a parity-gated path away from TradingView
as production-critical infrastructure.

Olive is a risk-first trading platform built in acceptance-gated phases. The current Phase 4 implementation securely receives, validates, and sizes candidate signals, but cannot place orders.

## Phase 0 capabilities

- Modular-monolith Python service layout
- Explicit development, testing, paper, staging, and production environment names
- Typed, environment-driven configuration
- JSON structured logging
- Liveness and dependency-aware readiness endpoints
- PostgreSQL and Redis connectivity
- Alembic migration baseline
- Docker image and local Docker Compose stack
- Unit and API tests

## Local startup

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start the stack: `docker compose up --build`.
3. Open `http://localhost:8000/health/live` and `http://localhost:8000/health/ready`.

Run migrations with:

```text
docker compose run --rm api alembic upgrade head
```

Run tests with a Python 3.12 environment containing the `dev` dependencies:

```text
pytest
```

See `docs/phase-0.md` for scope, acceptance criteria, and the Phase 1 boundary.

## Phase 1 capabilities

- Canonical assets, underlyings, instruments, venues, and venue-symbol mappings
- Account, portfolio, strategy, and immutable strategy-version schema foundations
- Fixed-precision instrument metadata for tick size, lot size, multiplier, and leverage
- Versioned asset-master API and deterministic venue-symbol resolution
- Migration-backed constraints and fail-safe validation

See `docs/phase-1.md` for the complete Phase 1 contract.

## Phase 2 capabilities

- HMAC-SHA256 authentication over the exact raw webhook body
- Timestamp freshness, single-use nonce replay protection, and Redis-backed rate limiting
- Strict versioned TradingView signal schema with timezone-aware timestamps and Decimal prices
- Canonical strategy-version and venue-instrument resolution
- Immutable duplicate signal protection and an intake ledger for received/rejected payloads
- Versioned `POST /api/v1/signals/tradingview` endpoint

See `docs/phase-2.md` for the complete Phase 2 security and acceptance contract.

### Run the Phase 2 live smoke test

With Docker Desktop running, execute:

```powershell
.\scripts\phase2-smoke.ps1
```

The command builds a temporary local stack, migrates and seeds PostgreSQL, sends a genuinely signed signal, confirms it advances to `RISK_REVIEW`, verifies nonce-replay and duplicate-ID rejection, then removes the temporary containers and volumes.

## Phase 3 capabilities

- Deny-by-default validation policies per strategy version
- Strategy/version, venue, instrument, underlying, and asset enablement checks
- Direction and timeframe permissions
- Entry/reference deviation and directional stop/target validation
- Minimum expected R:R and setup-score thresholds
- Timezone-aware weekday, regular-session, and overnight-session checks
- Persisted deterministic validation outcomes and `RISK_REVIEW` handoff

See `docs/phase-3.md` for the complete Phase 3 contract.

## Phase 4 capabilities

- Decimal stop-based risk sizing and lot-size rounding
- `APPROVED`, `APPROVED_WITH_REDUCED_SIZE`, and `REJECTED` outcomes
- Base/maximum trade-risk, notional, leverage, margin, instrument, and multiplier caps
- Deterministic binding-constraint explanations
- Version-bound risk policies and immutable decision evidence
- Neutral placeholders for later roadmap multipliers without implementing them prematurely

See `docs/phase-4.md` for the complete Phase 4 contract.

## Phase 5 capabilities

- Projected gross, net, long, and short exposure checks
- Open stop-risk, margin-utilization, and leverage limits
- Maximum concurrent-position enforcement
- Safe proportional size reduction using the most restrictive remaining capacity
- Persisted current state, projected state, limits, outcome, and reasons

See `docs/phase-5.md` for the complete Phase 5 contract.

## Phase 6 capabilities

- Versioned limits for instrument, underlying, strategy, asset class, sector, industry, theme, venue, account, and portfolio
- Gross notional, open stop-risk, margin, and position-count controls
- Multi-value classification membership and deterministic aggregation
- Most-restrictive-limit-wins sizing with complete evaluation evidence

See `docs/phase-6.md` for the complete Phase 6 contract.

## Phase 7 capabilities

- Rolling return correlations and deterministic connected-component clusters
- Maximum correlated-position and cluster stop-risk controls
- Transparent reduce/reject outcomes with persisted correlation evidence

See `docs/phase-7.md` for the complete Phase 7 contract.

## Phase 8 capabilities

- Bounded regime, correlation, drawdown, liquidity, signal-quality, strategy-health, and event-risk multipliers
- Fully reconstructed multiplier product, uncapped risk, hard caps, and final risk
- Base-risk ceiling enforcement and versioned policy evidence

See `docs/phase-8.md` for the complete Phase 8 contract.

## Phase 9 capabilities

- Daily, weekly, and monthly loss protection
- Portfolio and strategy drawdown throttle/halt controls
- Consecutive-loss and profit-giveback protection
- Most-restrictive-control decisions with reconstructable evidence

See `docs/phase-9.md` for the complete Phase 9 contract.

## Phase 10 capabilities

- Transparent five-state portfolio regime classification
- Independent volatility, correlation, drawdown, liquidity, and market-stress severities
- Conservative highest-severity selection
- Regime-specific risk, leverage, and new-position controls

See `docs/phase-10.md` for the complete Phase 10 contract.

## Phase 11 capabilities

- Normalized bid, ask, last, volume, and OHLCV contracts
- Source and receipt timestamps with explicit timezone requirements
- Deterministic stale and future-data detection
- Crossed-market, spread, and price-jump sanity checks
- Persistent quality status and human-readable reasons for every quote

See `docs/phase-11.md` for the complete Phase 11 contract.

## Phase 12 capabilities

- Spread, expected-slippage, ADV-participation, and order-book-participation controls
- Deterministic approve, reduce, split, defer, and reject actions
- Fail-closed handling for stale or invalid authoritative market data
- Persisted policies, binding limits, approved sizes, slice counts, and reasons

See `docs/phase-12.md` for the complete Phase 12 contract.

## Phases 13-17 capabilities

- Idempotent paper orders, partial fills, cancellations, positions, fees, and realized PnL
- Stop/target coverage, orphan-order, and protection-quantity verification
- Internal-versus-venue order, position, and balance reconciliation
- One deterministic sandbox connector with outage and rate-limit failure behavior
- Complete paper entry, fill, protection, reconciliation, exit, and analytics pipeline

See `docs/phase-13.md` through `docs/phase-17.md` for the individual contracts.

## Phases 18-22 capabilities

- Administrative command-center API backed by operational ledgers
- Immutable versioned configuration with dual approval for risk increases
- Viewer, Analyst, Trader, Risk Manager, Admin, and Super Admin permissions
- Reconstructable audit events for configuration and emergency actions
- Scoped entry pauses, order cancellation, position closure, and emergency-halt controls

See `docs/phase-18.md` through `docs/phase-22.md` for the individual contracts.

## Acceptance automation

The `Olive acceptance` workflow runs unit/static checks, validates the Alembic chain, builds the complete Compose stack, applies migrations, checks schema drift, and probes both health contracts. The next phase must not begin until this workflow passes in a Docker-capable runner.
