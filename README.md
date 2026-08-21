# Olive Trading Platform

Phase 0 establishes the architecture foundation for a risk-first trading platform. It contains no signal, risk-decision, order, execution, or trading behavior.

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

## Acceptance automation

The `Phase 0 acceptance` workflow runs unit/static checks, validates the Alembic chain, builds the complete Compose stack, applies migrations, and probes both health contracts. Phase 1 must not begin until this workflow passes in a Docker-capable runner.
