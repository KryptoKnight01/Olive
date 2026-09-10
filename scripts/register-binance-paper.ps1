param(
    [string]$EnvironmentFile = ".env.staging",
    [string[]]$Symbols = @("BTCUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT")
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

$ComposeArguments = @(
    "compose", "--env-file", $EnvironmentFile, "-f", "compose.staging.yaml",
    "run", "--rm", "--build", "api", "python", "-m", "olive.smoke.binance_paper",
    "--symbols"
) + $Symbols
docker @ComposeArguments
if ($LASTEXITCODE -ne 0) {
    throw "Binance paper instrument registration failed."
}

Write-Host "Registered Binance paper symbols: $($Symbols -join ', ')." -ForegroundColor Cyan
Write-Host "Use Venue BINANCE and the matching symbol in each TradingView strategy alert." -ForegroundColor Cyan
Write-Host "Live trading remains disarmed." -ForegroundColor Yellow
