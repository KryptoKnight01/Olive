param(
    [string]$EnvironmentFile = ".env.staging",
    [switch]$ConfirmReset
)

$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

if (-not $ConfirmReset) {
    throw "Reset not confirmed. Run again with -ConfirmReset after reviewing this script."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required and must be running."
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Missing $EnvironmentFile."
}

$ResetSql = @'
BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM signal_intake_records AS intake
        JOIN venue_instruments AS mapping ON mapping.id = intake.venue_instrument_id
        JOIN venues AS venue ON venue.id = mapping.venue_id
        WHERE venue.code = 'BINANCE'
    ) THEN
        RAISE EXCEPTION 'Reset refused: Binance signal evidence already exists.';
    END IF;
END
$$;

TRUNCATE TABLE signal_intake_records RESTART IDENTITY CASCADE;
TRUNCATE TABLE
    paper_fills,
    paper_orders,
    paper_positions,
    protection_assessments,
    reconciliation_runs,
    paper_pipeline_runs
RESTART IDENTITY CASCADE;

DELETE FROM venue_instruments AS mapping
USING venues AS venue
WHERE mapping.venue_id = venue.id
  AND venue.code = 'COINBASE'
  AND mapping.symbol = 'BTC-USD';

COMMIT;

SELECT venue.code AS venue, mapping.symbol
FROM venue_instruments AS mapping
JOIN venues AS venue ON venue.id = mapping.venue_id
ORDER BY venue.code, mapping.symbol;

SELECT
    (SELECT count(*) FROM signal_intake_records) AS signal_intakes,
    (SELECT count(*) FROM paper_pipeline_runs) AS paper_executions;
'@

$ComposeArguments = @(
    "compose", "--env-file", $EnvironmentFile, "-f", "compose.staging.yaml",
    "exec", "-T", "postgres", "psql", "-v", "ON_ERROR_STOP=1", "-U", "olive", "-d", "olive"
)
$ResetSql | docker @ComposeArguments
if ($LASTEXITCODE -ne 0) {
    throw "Staging smoke-evidence reset failed. No partial reset was committed."
}

Write-Host "Synthetic Coinbase evidence removed." -ForegroundColor Cyan
Write-Host "Binance registrations were preserved. Live trading remains disarmed." -ForegroundColor Yellow
