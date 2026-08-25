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
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed to start the Olive stack." }

    docker compose run --rm api alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

    docker compose run --rm api alembic check
    if ($LASTEXITCODE -ne 0) { throw "Database schema drift check failed." }

    docker compose run --rm api python -m olive.smoke.phase2 seed
    if ($LASTEXITCODE -ne 0) { throw "Phase 2 smoke data seeding failed." }

    docker compose run --rm api python -m olive.smoke.phase2 send
    if ($LASTEXITCODE -ne 0) { throw "Phase 2 signed-signal verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 risk
    if ($LASTEXITCODE -ne 0) { throw "Phase 4 risk-decision verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 portfolio
    if ($LASTEXITCODE -ne 0) { throw "Phase 5 portfolio-risk verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 hierarchy
    if ($LASTEXITCODE -ne 0) { throw "Phase 6 hierarchical-risk verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 correlation
    if ($LASTEXITCODE -ne 0) { throw "Phase 7 correlation-risk verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 dynamic
    if ($LASTEXITCODE -ne 0) { throw "Phase 8 dynamic-risk verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 protection
    if ($LASTEXITCODE -ne 0) { throw "Phase 9 loss-protection verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 regime
    if ($LASTEXITCODE -ne 0) { throw "Phase 10 portfolio-regime verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 market-data
    if ($LASTEXITCODE -ne 0) { throw "Phase 11 market-data verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 execution-risk
    if ($LASTEXITCODE -ne 0) { throw "Phase 12 execution-risk verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 paper-pipeline
    if ($LASTEXITCODE -ne 0) { throw "Phases 13-17 paper-pipeline verification failed." }

    docker compose run --rm api python -m olive.smoke.phase2 governance-controls
    if ($LASTEXITCODE -ne 0) { throw "Phases 18-22 governance verification failed." }

    Write-Host "Phase 2-22 end-to-end smoke test passed." -ForegroundColor Green
}
finally {
    docker compose down --volumes
    $env:OLIVE_SIGNAL_HMAC_SECRET = $previousSecret
    $env:OLIVE_SIGNAL_HMAC_KEY_ID = $previousKeyId
}
