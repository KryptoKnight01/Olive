param(
    [string]$EnvironmentFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
$ComposeFile = "compose.staging.yaml"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required and must be running."
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Missing $EnvironmentFile. Copy .env.staging.example to .env.staging and replace every CHANGE_ME value."
}

$environmentText = Get-Content -LiteralPath $EnvironmentFile -Raw
if ($environmentText -match "CHANGE_ME") {
    throw "$EnvironmentFile still contains CHANGE_ME placeholders. Replace them before staging startup."
}

docker compose --env-file $EnvironmentFile -f $ComposeFile config --quiet
if ($LASTEXITCODE -ne 0) { throw "Staging Compose configuration is invalid." }

docker compose --env-file $EnvironmentFile -f $ComposeFile up --build --detach --wait
if ($LASTEXITCODE -ne 0) { throw "Staging services failed to start." }

docker compose --env-file $EnvironmentFile -f $ComposeFile run --rm api alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Staging database migration failed." }

docker compose --env-file $EnvironmentFile -f $ComposeFile run --rm api alembic check
if ($LASTEXITCODE -ne 0) { throw "Staging database schema drift was detected." }

$portLine = Get-Content -LiteralPath $EnvironmentFile | Where-Object { $_ -match '^OLIVE_STAGING_PORT=' }
$port = if ($portLine) { ($portLine -split '=', 2)[1].Trim() } else { "8000" }
$live = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health/live" -TimeoutSec 10
$ready = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health/ready" -TimeoutSec 10

if ($live.environment -ne "staging" -or $ready.status -ne "ready") {
    throw "Staging health contracts did not pass."
}

Write-Host "Olive staging is ready at http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "Live trading remains disarmed; no venue credentials were configured." -ForegroundColor Yellow

