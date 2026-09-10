param(
    [string]$EnvironmentFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required and must be running."
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Missing $EnvironmentFile."
}

docker compose --env-file $EnvironmentFile -f compose.staging.yaml run --rm --build api `
    python -m olive.smoke.binance_paper
if ($LASTEXITCODE -ne 0) {
    throw "Binance paper instrument registration failed."
}

Write-Host "Use Venue BINANCE and Instrument BTCUSDT in the TradingView strategy settings." -ForegroundColor Cyan
Write-Host "Live trading remains disarmed." -ForegroundColor Yellow
