param(
    [string]$EnvironmentFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
$ComposeArguments = @(
    "compose",
    "--env-file", $EnvironmentFile,
    "-f", "compose.staging.yaml",
    "-f", "compose.tradingview-tunnel.yaml"
)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required and must be running."
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Missing $EnvironmentFile."
}
$secretLine = Get-Content -LiteralPath $EnvironmentFile |
    Where-Object { $_ -match '^OLIVE_TRADINGVIEW_WEBHOOK_SECRET=' }
$secret = if ($secretLine) { ($secretLine -split '=', 2)[1].Trim() } else { "" }
if ($secret.Length -lt 32) {
    throw "OLIVE_TRADINGVIEW_WEBHOOK_SECRET must contain at least 32 characters."
}

docker @ComposeArguments up --detach tradingview-ingress tradingview-tunnel
if ($LASTEXITCODE -ne 0) { throw "TradingView tunnel failed to start." }

$publicBase = $null
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $logs = docker @ComposeArguments logs --no-color tradingview-tunnel 2>&1 | Out-String
    $match = [regex]::Match($logs, 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($match.Success) {
        $publicBase = $match.Value
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $publicBase) {
    throw "The tunnel started but did not publish a URL. Check Docker logs for tradingview-tunnel."
}

$webhookUrl = "$publicBase/api/v1/signals/tradingview-alert"
Write-Host "TradingView paper tunnel is ready." -ForegroundColor Green
Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Cyan
Write-Host "Only the TradingView alert route is exposed; all other paths return 404." -ForegroundColor Green
Write-Host "This testing URL changes if the tunnel container restarts." -ForegroundColor Yellow
Write-Host "Live trading remains disarmed." -ForegroundColor Yellow
