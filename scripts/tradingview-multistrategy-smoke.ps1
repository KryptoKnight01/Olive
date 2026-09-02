param(
    [string]$EnvironmentFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
$ComposeArguments = @(
    "compose",
    "--env-file", $EnvironmentFile,
    "-f", "compose.staging.yaml",
    "-f", "compose.tradingview-tunnel.yaml",
    "-f", "compose.tradingview-named-tunnel.yaml"
)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required and must be running."
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Missing $EnvironmentFile."
}

$hostnameLine = Get-Content -LiteralPath $EnvironmentFile |
    Where-Object { $_ -match '^OLIVE_TRADINGVIEW_PUBLIC_HOSTNAME=' } |
    Select-Object -First 1
$hostname = if ($hostnameLine) { ($hostnameLine -split '=', 2)[1].Trim() } else { "" }
if ($hostname -notmatch '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$') {
    throw "OLIVE_TRADINGVIEW_PUBLIC_HOSTNAME must be configured."
}

$webhookUrl = "https://$hostname/api/v1/signals/tradingview-alert"
docker @ComposeArguments run --rm --build api `
    python -m olive.smoke.multistrategy --url $webhookUrl
if ($LASTEXITCODE -ne 0) {
    throw "Multi-strategy paper test failed."
}

Write-Host "Refresh the Olive dashboard to see two additional paper executions." -ForegroundColor Cyan
Write-Host "Live trading remains disarmed." -ForegroundColor Yellow
