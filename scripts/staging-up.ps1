param(
    [string]$EnvironmentFile = ".env.staging"
)

$ErrorActionPreference = "Stop"

# Docker BuildKit writes normal progress messages to stderr. PowerShell 7 can
# promote those messages to terminating errors when ErrorActionPreference is
# Stop, preventing us from checking Docker's actual exit code below.
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}
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
$webPortLine = Get-Content -LiteralPath $EnvironmentFile | Where-Object { $_ -match '^OLIVE_WEB_PORT=' }
$webPort = if ($webPortLine) { ($webPortLine -split '=', 2)[1].Trim() } else { "3000" }
$adminTokenLine = Get-Content -LiteralPath $EnvironmentFile | Where-Object { $_ -match '^OLIVE_ADMIN_API_KEY=' }
$adminToken = if ($adminTokenLine) { ($adminTokenLine -split '=', 2)[1].Trim() } else { "" }
$live = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health/live" -TimeoutSec 10
$ready = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health/ready" -TimeoutSec 10

if ($live.environment -ne "staging" -or $ready.status -ne "ready") {
    throw "Staging health contracts did not pass."
}

$webBase = "http://127.0.0.1:$webPort"
$webReady = $false
for ($attempt = 1; $attempt -le 12; $attempt++) {
    try {
        $page = Invoke-WebRequest -Uri $webBase -UseBasicParsing -TimeoutSec 10
        if ($page.StatusCode -eq 200 -and $page.Content -match "Olive") {
            $webReady = $true
            break
        }
    } catch {
        if ($attempt -eq 12) { throw "Olive dashboard did not become ready at $webBase." }
    }
    Start-Sleep -Seconds 2
}
if (-not $webReady) { throw "Olive dashboard readiness contract did not pass." }

try {
    Invoke-WebRequest -Uri "$webBase/api/dashboard" -UseBasicParsing -TimeoutSec 10 | Out-Null
    throw "Anonymous dashboard access was unexpectedly accepted."
} catch {
    $anonymousStatus = [int]$_.Exception.Response.StatusCode
    if ($anonymousStatus -ne 401) { throw }
}

if (-not $adminToken) { throw "OLIVE_ADMIN_API_KEY is required for dashboard verification." }
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$signInBody = @{ token = $adminToken } | ConvertTo-Json -Compress
$signIn = Invoke-RestMethod -Uri "$webBase/api/session" -Method Post -ContentType "application/json" -Body $signInBody -WebSession $session -TimeoutSec 10
if (-not $signIn.authenticated) { throw "Dashboard sign-in contract did not pass." }
$dashboard = Invoke-RestMethod -Uri "$webBase/api/dashboard" -WebSession $session -TimeoutSec 10
if ($null -eq $dashboard.summary -or $null -eq $dashboard.executions) {
    throw "Dashboard monitoring contract did not pass."
}

Write-Host "Olive staging is ready at http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "Olive admin dashboard is ready at $webBase" -ForegroundColor Green
Write-Host "Dashboard authentication and monitoring contracts passed." -ForegroundColor Green
Write-Host "Live trading remains disarmed; no venue credentials were configured." -ForegroundColor Yellow

