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

$environmentLines = Get-Content -LiteralPath $EnvironmentFile
$tokenLine = $environmentLines | Where-Object { $_ -match '^CLOUDFLARE_TUNNEL_TOKEN=' }
$token = if ($tokenLine) { ($tokenLine -split '=', 2)[1].Trim() } else { "" }
$hostnameLine = $environmentLines | Where-Object { $_ -match '^OLIVE_TRADINGVIEW_PUBLIC_HOSTNAME=' }
$hostname = if ($hostnameLine) { ($hostnameLine -split '=', 2)[1].Trim() } else { "" }

if ($token.Length -lt 32) {
    throw "CLOUDFLARE_TUNNEL_TOKEN must contain the named tunnel token."
}
if ($hostname -notmatch '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$') {
    throw "OLIVE_TRADINGVIEW_PUBLIC_HOSTNAME must be a valid hostname."
}

docker @ComposeArguments up --detach --force-recreate tradingview-ingress tradingview-tunnel
if ($LASTEXITCODE -ne 0) { throw "Named TradingView tunnel failed to start." }

$connected = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $logs = docker @ComposeArguments logs --no-color tradingview-tunnel 2>&1 | Out-String
    if ($logs -match 'Registered tunnel connection') {
        $connected = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $connected) {
    throw "The named tunnel did not connect to Cloudflare. Check its Docker logs."
}

$webhookUrl = "https://$hostname/api/v1/signals/tradingview-alert"
Write-Host "Permanent TradingView paper tunnel is ready." -ForegroundColor Green
Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Cyan
Write-Host "Only the TradingView alert route is exposed; all other paths return 404." -ForegroundColor Green
Write-Host "The hostname remains stable across container restarts." -ForegroundColor Green
Write-Host "Live trading remains disarmed." -ForegroundColor Yellow

