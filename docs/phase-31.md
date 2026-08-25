# Phase 31 — Multi-Strategy Support

Strategy signals are resolved deterministically by priority, direction and the shared portfolio
risk budget. Opposing lower-priority signals are rejected and same-direction allocations are
capped when they compete for the remaining risk budget.
