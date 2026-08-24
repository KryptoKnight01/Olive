$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Install/start Docker Desktop, then run this command again."
}

$previousSecret = $env:OLIVE_SIGNAL_HMAC_SECRET
$previousKeyId = $env:OLIVE_SIGNAL_HMAC_KEY_ID
$env:OLIVE_SIGNAL_HMAC_SECRET = "olive-phase2-local-smoke-only"
$env:OLIVE_SIGNAL_HMAC_KEY_ID = "tradingview-development"

try {
    docker compose up --build --detach --wait
    docker compose run --rm api alembic upgrade head
    docker compose run --rm api python -m olive.smoke.phase2 seed
    docker compose run --rm api python -m olive.smoke.phase2 send
    Write-Host "Phase 2 end-to-end smoke test passed." -ForegroundColor Green
}
finally {
    docker compose down --volumes
    $env:OLIVE_SIGNAL_HMAC_SECRET = $previousSecret
    $env:OLIVE_SIGNAL_HMAC_KEY_ID = $previousKeyId
}
