# Phase 3 — Signal Validation Engine

## 1. Phase objective

Deterministically validate authenticated candidate signals against enabled strategy, instrument, price-logic, quality, direction, timeframe, and session policy before they may enter risk review.

## 2. Existing system assumptions

- Phase 0–2 acceptance gates pass.
- Authenticated signals already resolve to canonical strategy versions and venue instruments.
- Signals remain proposals; `RISK_REVIEW` is not approval to trade.

## 3. Scope

- Versioned per-strategy validation policies
- Strategy/version and asset-master enablement
- Direction and timeframe permissions
- Entry/reference deviation, stop/target logic, minimum R:R, and setup-score rules
- Timezone, weekday, regular, and overnight session checks
- Persisted deterministic validation outcomes and rejection reasons

## 4. Non-scope

- Position sizing, trade-risk approval, portfolio exposure, market-data freshness, orders, execution, positions, or administration UI

## 5. Architecture changes

The modular monolith gains a `validation` layer. The gateway resolves canonical entities, loads the applicable policy, invokes the deterministic engine, and persists either `REJECTED` or `RISK_REVIEW`.

## 6. Database changes

Revision `20260824_0004` creates `signal_validation_policies`, extends intake status with `RISK_REVIEW`, and adds validation details and timestamps to the intake ledger.

## 7. API changes

The existing signed webhook remains the entry point. Valid signals return HTTP 202 with `RISK_REVIEW`. Rule failures return HTTP 422 with a stable code and persisted intake ID.

## 8. Configuration changes

Policies define enablement, directions, timeframes, maximum entry deviation, minimum R:R/setup score, timezone, weekday set, and optional session start/end. Missing policy denies validation by default.

## 9. Security considerations

Authentication and replay protection still run before validation. Validation details contain rule inputs and outcomes, never signing secrets.

## 10. Risk considerations

Validation is a prerequisite only. It cannot approve size, capital, leverage, margin, or execution. Phase 4 retains the first risk-decision authority.

## 11. Implementation

Policy persistence is in `src/olive/validation/models.py`; deterministic rules are in `src/olive/validation/service.py`; gateway orchestration remains in `src/olive/gateway/service.py`.

## 12. Automated tests

Tests cover passing signals, entry deviation, long/short stop-target logic, R:R, setup score, timeframe, direction, weekday/session, disabled strategy/instrument, persistence, and Phase 0–2 regressions.

## 13. Failure cases

Missing/disabled policy, inactive strategy/version/venue/instrument/underlying/assets, prohibited direction/timeframe, excessive deviation, illogical prices, low quality, closed session, and invalid session configuration all fail closed.

## 14. Run instructions

Apply `alembic upgrade head`, create one policy for every enabled strategy version, then submit signals through the authenticated Phase 2 endpoint.

## 15. Test instructions

Run `pytest`, `ruff check .`, `mypy src`, the migration/schema-drift checks, and `scripts/phase2-smoke.ps1` with Docker Desktop running.

## 16. Acceptance criteria

- All configured rules produce deterministic pass/fail outcomes.
- Every failed authenticated signal is persisted with a stable code and explanation.
- Passing signals advance only to `RISK_REVIEW`.
- Missing, disabled, or inconsistent policy/data fails closed.
- PostgreSQL migration and all Phase 0–2 regressions pass.

## 17. Regression check

Health, asset master, webhook authentication, replay protection, duplicate protection, schema validation, and environment separation remain green.

## 18. Known limitations

Session holidays and early closes are not modeled; Phase 11 supplies fresh reference-market data; policy administration UI and immutable approval workflow are deferred to Phases 18–20.

## 19. Next phase only

Phase 4 introduces stop-based single-trade risk sizing with notional, leverage, margin, instrument, and contract-multiplier caps. It is not implemented in Phase 3.
