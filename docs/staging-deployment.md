# Olive Staging Deployment

This baseline runs Olive locally in the staging environment with persistent PostgreSQL and Redis
data, internal-only database/cache networking, a localhost-bound API, automatic restarts,
container privilege reduction, health checks, migrations and schema-drift verification.

## Start staging on Windows

1. Copy `.env.staging.example` to `.env.staging`.
2. Replace every `CHANGE_ME` value with a long random value.
3. Start Docker Desktop.
4. In PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
5. Run `.\scripts\staging-up.ps1`.
6. Confirm the script reports that staging is ready.

## Stop staging

Run `.\scripts\staging-down.ps1`. Data volumes are preserved. Do not add `--volumes` unless the
staging data has been backed up and deliberate deletion is intended.

## Security boundary

The staging file does not accept or store venue credentials and does not arm live trading. Keep
`.env.staging` outside version control. A remote staging deployment additionally needs managed
TLS, a secrets manager, off-host backups, monitoring, access control and network restrictions.

