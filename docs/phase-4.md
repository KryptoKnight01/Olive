# Phase 4 — Basic Single-Trade Risk Engine

## 1. Phase objective

Produce deterministic stop-based position sizes and `APPROVED`, `APPROVED_WITH_REDUCED_SIZE`, or `REJECTED` decisions for Phase 3-validated signals.

## 2. Existing system assumptions

Phases 0–3 pass; signals reach `RISK_REVIEW`; canonical instruments contain fixed-point price, lot, multiplier, and leverage data.

## 3. Scope

Base/maximum risk, stop-distance boundaries, lot rounding, contract multiplier, notional, leverage, available-margin, and maximum-margin caps; immutable decision evidence.

## 4. Non-scope

Portfolio exposure, correlations, dynamic multipliers, market liquidity, orders, execution, positions, and user-facing administration.

## 5. Architecture changes

An internal `risk` layer separates immutable input/output contracts, pure calculation, persistence models, and orchestration. No public order-capable endpoint is introduced.

## 6. Database changes

Revision `20260824_0005` creates version-bound single-trade risk policies and one immutable risk decision per signal intake.

## 7. API changes

None. Risk evaluation is an internal service boundary until authenticated administration and workflow APIs are introduced.

## 8. Configuration changes

Each strategy version requires base/max risk, max notional/leverage/margin, and min/max stop-distance policy values.

## 9. Security considerations

TradingView cannot provide trusted equity, margin, limits, or risk decisions. Capital snapshots enter through the internal service contract.

## 10. Risk considerations

All financial math uses `Decimal`; the most restrictive size cap wins; size rounds down to the instrument lot; missing policy/state fails closed.

## 11. Implementation

Contracts, engine, models, and orchestration are under `src/olive/risk`.

## 12. Automated tests

Tests cover approval, risk capping, notional/margin/leverage reductions, stop boundaries, zero capacity, inconsistent policy, lot rounding, and contract multipliers.

## 13. Failure cases

Ineligible signal, missing canonical data/policy, equal/invalid stop distance, inconsistent limits, zero capacity, and sub-lot size reject or fail closed.

## 14. Run instructions

Apply migrations, configure a risk policy for each enabled strategy version, and invoke the internal service with authoritative equity and margin snapshots.

## 15. Test instructions

Run `pytest`, `ruff check .`, `mypy src`, migration/schema-drift checks, and the Docker smoke script.

## 16. Acceptance criteria

Every decision satisfies the master risk-decision contract, is explainable, uses fixed-point math, honors every Phase 4 cap, persists its snapshots, and passes all earlier regressions.

## 17. Regression check

Health, asset master, secure intake, replay protection, validation, migration, and schema-drift gates remain green.

## 18. Known limitations

Equity and available margin are supplied snapshots; portfolio aggregation begins in Phase 5. Advanced multipliers remain neutral at `1` until their roadmap phases.

## 19. Next phase only

Phase 5 adds projected post-trade portfolio equity, exposure, stop risk, margin, leverage, and concurrent-position limits. It is not implemented here.
