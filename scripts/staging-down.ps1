param(
    [string]$EnvironmentFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
docker compose --env-file $EnvironmentFile -f compose.staging.yaml down
if ($LASTEXITCODE -ne 0) { throw "Olive staging shutdown failed." }
Write-Host "Olive staging services stopped. Persistent data volumes were preserved." -ForegroundColor Green

