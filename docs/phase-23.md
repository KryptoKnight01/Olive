# Phase 23 — Strategy Performance Monitor

Olive evaluates profit factor, win rate, expectancy, average R, drawdown, trade frequency,
slippage and holding time. Deterministic thresholds assign GREEN, YELLOW, ORANGE or RED
health and preserve the breached controls as evidence.

Acceptance is covered by `tests/test_live_readiness.py` and the Docker smoke workflow.
