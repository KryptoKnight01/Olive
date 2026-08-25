# Phase 20 — RBAC and Security

Olive defines Viewer, Analyst, Trader, Risk Manager, Admin, and Super Admin roles with deny-by-default permission checks for viewing, trading, risk, configuration, user administration, and kill-switch operation. User security records retain MFA state and session expiry.

Migration `20260825_0021` creates user-role security records. External identity-provider integration is deferred.
