# Automatic paper orchestration

Olive can automatically continue a successfully authenticated and validated TradingView
signal through single-trade risk sizing and the deterministic paper pipeline. The workflow is
opt-in and is permitted only when the application environment is `paper` or `staging`.

The synchronous acceptance path is:

1. Authenticate the exact webhook body with HMAC-SHA256.
2. Reject stale, replayed, duplicated, mismatched, or invalid signals.
3. Persist the validated intake at `RISK_REVIEW`.
4. Evaluate the configured single-trade risk policy.
5. Execute a sandbox-only paper round trip using the approved quantity.
6. Verify protection and reconcile the in-memory paper venue.
7. Persist the paper pipeline outcome and return it in `paper_execution`.

`OLIVE_PAPER_AUTO_EXECUTE=true` enables the bridge. Equity, available margin, requested risk,
and the simulated fee rate are explicit environment settings. Production rejects this setting
during application configuration validation. The connector used by this workflow has no live
venue client, credentials, or routing capability.

The first implementation supports `LONG` signals only. A `SHORT` signal remains safely recorded
at intake and receives a rejected paper-execution outcome until short-side pipeline support is
implemented.
