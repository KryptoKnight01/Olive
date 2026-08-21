# Phase 0 — Architecture Foundation

## 1. Phase objective

Create an independently testable, container-ready architecture foundation for the Olive Trading Platform without implementing trading behavior.

## 2. Existing system assumptions

- This repository begins from zero.
- TradingView and Olive Liquidity Compass are future signal sources only.
- PostgreSQL and Redis are the initial persistence and cache/coordination technologies.
- The initial delivery shape is a modular monolith.

## 3. Scope

- Repository and service skeleton
- Development, testing, paper, staging, and production environment names
- Typed configuration and structured JSON logging
- FastAPI liveness and readiness endpoints
- PostgreSQL and Redis clients with bounded dependency checks
- Alembic migration baseline
- Docker image and local Compose stack
- Automated configuration, logging, and API tests

## 4. Non-scope

- Trading signals, webhooks, validation, risk decisions, sizing, orders, fills, positions, venue connectors, market data, analytics, authentication, RBAC, admin UI, or mobile UI
- Domain entities reserved for Phase 1
- Production cloud topology, high availability, and live credentials

## 5. Architecture changes

The project starts as a modular monolith under `src/olive`. The API layer depends on infrastructure health abstractions rather than embedding database/cache logic in routes. Future domain modules can be added without changing the Phase 0 boundary.

## 6. Database changes

Alembic is configured with an initial empty baseline revision. No domain tables are created prematurely.

## 7. API changes

- `GET /health/live`: process liveness; does not require dependencies.
- `GET /health/ready`: PostgreSQL and Redis readiness; returns HTTP 503 if either dependency is unavailable.

## 8. Configuration changes

All settings use the `OLIVE_` prefix. Environment, service metadata, log level, connection URLs, and dependency timeout are configurable. Secrets are not committed.

## 9. Security considerations

- No production credentials are included.
- `.env` files are ignored.
- The container runs as a non-root user.
- Dependency failures expose exception types only, not connection strings or secrets.

## 10. Risk considerations

There is no trading risk logic in Phase 0. Operational behavior fails closed at readiness: unavailable PostgreSQL or Redis marks the service not ready.

## 11. Implementation

Implementation is contained in the repository root, `src/olive`, `migrations`, `tests`, and container definitions.

## 12. Automated tests

- Explicit environment enumeration and invalid-environment rejection
- Configuration boundary validation
- Liveness independence from infrastructure
- Readiness success with healthy dependencies
- Readiness HTTP 503 when a dependency fails
- Structured logging JSON and context fields

## 13. Failure cases

- PostgreSQL unavailable, timeout, or query failure
- Redis unavailable, timeout, or ping failure
- Invalid environment name
- Invalid dependency timeout

## 14. Run instructions

Copy `.env.example` to `.env`, then run `docker compose up --build`. Apply migrations with `docker compose run --rm api alembic upgrade head`.

## 15. Test instructions

Install the project with its `dev` dependencies in Python 3.12 and run `pytest`. Run `ruff check .` and `mypy src` for static verification.

The `Phase 0 acceptance` CI workflow repeats those checks and performs the Docker Compose startup, migration, liveness, and readiness smoke test on a Docker-capable runner.

## 16. Acceptance criteria

- Application starts through Docker Compose.
- Liveness returns HTTP 200.
- Readiness returns HTTP 200 with PostgreSQL and Redis available.
- Readiness returns HTTP 503 when either required dependency is unavailable.
- Alembic upgrades to the Phase 0 head revision.
- Automated tests and static checks pass.
- No trading or Phase 1 domain behavior is present.
- The `Phase 0 acceptance` workflow passes, including its Compose smoke test.

## 17. Regression check

Phase 0 establishes the initial baseline. Later phases must preserve health, configuration, migration, container startup, and test behavior.

## 18. Known limitations

- Local Compose is a development topology, not a production deployment.
- No metrics, tracing backend, secrets manager, backup system, or high-availability topology is implemented yet.
- Readiness is an immediate dependency snapshot and does not provide historical health data.

## 19. Next phase only

Phase 1 introduces the domain model and asset master. It is documented here only as the next boundary and is not implemented.
