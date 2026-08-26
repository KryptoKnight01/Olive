# Admin API authentication

Every `/api/v1/admin` endpoint requires an `Authorization: Bearer <token>` header. The server
compares the supplied token with `OLIVE_ADMIN_API_KEY` using constant-time verification and then
authorizes the server-configured `OLIVE_ADMIN_API_ROLE` against Olive's role-permission matrix.

The initial staging principal defaults to `VIEWER`, which grants read-only monitoring access.
Missing or invalid credentials return `401`; an unconfigured server fails closed with `503`; and
a role without the required permission returns `403`.

The key must contain at least 32 characters, is represented as a secret in application settings,
and must never be committed. This baseline is suitable for private staging. Multi-user identity,
short-lived sessions, MFA, and key rotation are required before public or production exposure.
