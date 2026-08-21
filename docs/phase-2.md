# Phase 2 — Secure TradingView Signal Gateway

## 1. Phase objective

Receive authenticated TradingView candidate signals through a versioned, replay-resistant, rate-limited gateway and persist deterministic intake outcomes. Signals remain proposals and cannot create risk decisions or orders.

## 2. Existing system assumptions

- Phase 0 and Phase 1 acceptance gates pass.
- Canonical strategy versions and venue-instrument mappings already exist.
- PostgreSQL is authoritative for the signal intake ledger; Redis is required for replay and rate-limit controls.

## 3. Scope

- Versioned TradingView webhook endpoint
- HMAC-SHA256 authentication of timestamp, nonce, and exact raw body
- Timestamp freshness, single-use nonce, rate limiting, and payload-size controls
- Strict signal schema with required and optional metadata
- Strategy-version, configuration-version, venue, and instrument resolution
- Received/rejected intake persistence and duplicate signal-ID prevention

## 4. Non-scope

- Strategy enablement policy, directional permission, entry deviation, stop/target logic, minimum R:R, setup-score thresholds, sessions, or fresh market-data validation
- Risk approval, sizing, portfolio controls, orders, execution, positions, or UI
- Phase 3 validation-state transitions beyond `RECEIVED` and `REJECTED`

## 5. Architecture changes

The modular monolith gains a gateway layer for authentication, strict schemas, deterministic errors, and intake orchestration. The HTTP route reads the raw body and authenticates it before signal parsing. Domain lookup and persistence remain outside the route.

## 6. Database changes

Revision `20260821_0003` creates `signal_intake_records`. It stores payload hashes, sanitized rejection details, canonical references, Decimal signal values, timestamps, payload JSON, and immutable unique signal IDs.

## 7. API changes

`POST /api/v1/signals/tradingview` requires `X-Olive-Key-Id`, `X-Olive-Timestamp`, `X-Olive-Nonce`, and `X-Olive-Signature`. The signature is the lowercase hexadecimal HMAC-SHA256 of `timestamp + newline + nonce + newline + raw body`, optionally prefixed by `sha256=`.

Accepted inputs return HTTP 202 with intake ID, signal ID, and `RECEIVED`. Authentication failures return 401, replay/duplicate failures 409, rate limits 429, dependency failures 503, and authenticated payload rejections 422 with a persisted intake ID where possible.

## 8. Configuration changes

Gateway key ID, secret, freshness window, nonce TTL, rate limit/window, and maximum payload size use `OLIVE_SIGNAL_*` environment settings. The secret has no usable default and is represented as a redacted secret value.

## 9. Security considerations

- Raw bytes are authenticated before parsing or persistence.
- Signatures and key IDs use constant-time comparison where appropriate.
- Nonces are reserved atomically in Redis and remain reserved for the complete freshness window.
- Redis failure rejects intake rather than bypassing replay controls.
- Secrets are never returned, persisted, or intentionally logged.
- Oversized payloads are rejected before cryptographic or schema work.

## 10. Risk considerations

No trading or portfolio risk decision is made. `RECEIVED` means authenticated and mapped only; it does not mean approved, valid for trading, or sized.

## 11. Implementation

Gateway code is under `src/olive/gateway`; its HTTP adapter is `src/olive/api/signal_gateway.py`; the intake ledger is migration-backed.

## 12. Automated tests

Tests cover valid signatures, tampering, stale timestamps, reused and concurrently reused nonces, rate limits, Redis failure, secret redaction, configuration boundaries, accepted persistence, duplicates, unknown mappings, malformed JSON persistence, and authentication-before-parsing. All earlier tests remain regression checks.

## 13. Failure cases

- Missing/invalid key, timestamp, nonce, or signature
- Stale webhook or signal timestamp
- Replayed nonce or duplicate signal ID
- Rate-limit breach or Redis outage
- Oversized, malformed, or schema-invalid payload
- Environment mismatch
- Unknown strategy/configuration version or venue-instrument mapping
- Database uniqueness race

## 14. Run instructions

Set a strong environment-specific `OLIVE_SIGNAL_HMAC_SECRET`, start the stack, and apply `alembic upgrade head`. Never reuse development/test secrets in paper, staging, or production.

## 15. Test instructions

Run `pytest`, `ruff check .`, `mypy src`, `alembic upgrade head`, and `alembic check`. CI repeats these checks against PostgreSQL, Redis, and the container image.

## 16. Acceptance criteria

- Correctly signed, fresh, mapped schema-v1 signals persist as `RECEIVED` and return HTTP 202.
- Authentication is performed over exact raw bytes before parsing.
- Invalid signatures, stale timestamps, replayed nonces, duplicates, rate excess, and dependency failures fail closed.
- Authenticated malformed, stale, expired, environment-mismatched, or unknown inputs have deterministic rejection codes and persisted intake evidence where safe.
- PostgreSQL migration and schema-drift checks pass.
- All Phase 0–1 regression checks pass.
- No Phase 3 validation or trading behavior exists.

## 17. Regression check

Health, configuration, logging, containers, canonical mappings, Decimal constraints, and existing asset-master APIs remain green.

## 18. Known limitations

- One configured HMAC key is supported per deployed service instance; managed multi-key rotation is deferred.
- Rate limiting is per key ID, not per source IP.
- Authenticated malformed raw bytes persist as a hash and rejection record, not as raw invalid JSON.
- No external secrets manager, TLS termination, or IP allowlist is configured in the local Compose topology.

## 19. Next phase only

Phase 3 introduces the signal validation engine. It is not implemented in Phase 2.
