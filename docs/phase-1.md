# Phase 1 — Domain Model & Asset Master

## 1. Phase objective

Create canonical, migration-backed identities for assets, economic underlyings, tradable instruments, venues, accounts, portfolios, strategies, and strategy versions.

## 2. Existing system assumptions

- The Phase 0 architecture foundation and acceptance workflow pass.
- Venue symbols are external identifiers, not canonical internal identity.
- Missing or inconsistent mappings must fail closed.

## 3. Scope

- UUID-based domain identities and explicit lifecycle enums
- Asset, underlying, instrument, venue, venue-instrument, account, portfolio, strategy, and strategy-version tables
- Fixed-precision instrument constraints
- Canonical venue-symbol resolution API
- Asset-master create/list operations needed to test the mapping chain

## 4. Non-scope

- Signal intake, signal validation, risk, sizing, execution, orders, positions, market data, authentication, permissions, admin UI, or venue connectivity
- Configuration management workflows and approval UI
- Tradeable enablement or risk limits

## 5. Architecture changes

The modular monolith gains a domain layer containing models, schemas, deterministic errors, and an asset-master service. API routes remain thin and delegate domain behavior to the service.

## 6. Database changes

Revision `20260821_0002` creates nine Phase 1 tables with uniqueness, referential integrity, lifecycle, and positive fixed-precision constraints. Restrictive foreign keys prevent deletion of referenced canonical records.

## 7. API changes

Versioned `/api/v1/asset-master` endpoints create assets, underlyings, instruments, venues, and venue mappings; list assets; and resolve a venue code and symbol to canonical instrument and underlying IDs.

## 8. Configuration changes

No new runtime settings are required.

## 9. Security considerations

Account records store an external reference only; credentials and secrets are excluded. API authentication remains out of scope until its approved phase.

## 10. Risk considerations

Phase 1 performs no risk decisions. Unknown mappings and inconsistent asset-class/base-asset relationships are rejected rather than guessed.

## 11. Implementation

Domain code is under `src/olive/domain`; HTTP adapters are under `src/olive/api`; schema changes are in the Phase 1 Alembic revision.

## 12. Automated tests

Tests cover schema registration, fixed precision, canonical mapping resolution, case normalization, duplicate prevention, cross-entity consistency, and unknown mapping rejection. All Phase 0 tests remain regression checks.

## 13. Failure cases

- Duplicate canonical codes or venue mappings
- Missing referenced entity
- Underlying asset-class mismatch
- Instrument/base-underlying mismatch
- Non-positive tick, lot, or multiplier values
- Unknown venue symbol

## 14. Run instructions

Start the Phase 0 stack and run `alembic upgrade head`. The new API appears under `/api/v1/asset-master` and in the generated OpenAPI specification.

## 15. Test instructions

Run `pytest`, `ruff check .`, `mypy src`, and the migration-chain validation. The CI acceptance workflow also applies migrations to PostgreSQL and probes service readiness.

## 16. Acceptance criteria

- All nine domain tables migrate successfully on PostgreSQL.
- Canonical venue symbols resolve deterministically to instrument and underlying IDs.
- Duplicate, missing, or inconsistent records are rejected with structured errors.
- Critical numeric instrument fields use fixed precision and enforce positive values.
- Phase 0 regression, lint, type, migration, and container checks pass.
- No Phase 2 signal gateway behavior exists.

## 17. Regression check

Phase 0 liveness, readiness, configuration, logging, migration, and container behavior must remain green.

## 18. Known limitations

- CRUD coverage is intentionally limited to the asset-master chain needed for Phase 1 validation.
- Lifecycle transitions, audit history, configuration versions, authentication, and bulk import are deferred.
- Taxonomy fields are present but no external classification provider is integrated.

## 19. Next phase only

Phase 2 introduces the secure TradingView signal gateway. It is not implemented in Phase 1.

