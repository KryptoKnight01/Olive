param(
    [string]$EnvironmentFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
docker compose --env-file $EnvironmentFile `
    -f compose.staging.yaml `
    -f compose.tradingview-tunnel.yaml `
    stop tradingview-tunnel tradingview-ingress
if ($LASTEXITCODE -ne 0) { throw "TradingView tunnel shutdown failed." }
Write-Host "TradingView paper tunnel stopped. Olive staging remains running locally." -ForegroundColor Green
