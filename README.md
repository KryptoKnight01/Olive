# Olive Trading Platform

Olive is a risk-first trading platform built in acceptance-gated phases. The current Phase 3 implementation securely receives and validates candidate signals, but makes no risk decision and cannot place orders.

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

## Acceptance automation

The `Olive acceptance` workflow runs unit/static checks, validates the Alembic chain, builds the complete Compose stack, applies migrations, checks schema drift, and probes both health contracts. The next phase must not begin until this workflow passes in a Docker-capable runner.
