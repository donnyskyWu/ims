# One-command IMS Playwright E2E: preflight API (18080) + Vite (6173), run full suite, write e2e_result.txt.
# DB: loads ims-backend/.env before starting API (local MySQL vs cloud — see doc/运维/云MySQL联调.md).
param(
    [switch]$SkipServe,
    [int]$ApiWaitSec = 120,
    [int]$WebWaitSec = 90
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$WebRoot = (Get-Location).Path
$BackendRoot = Join-Path (Split-Path $WebRoot -Parent) "ims-backend"

$ApiPort = if ($env:IMS_PORT) { [int]$env:IMS_PORT } else { 18080 }
$WebPort = 6173
$ApiBase = "http://127.0.0.1:$ApiPort"
$WebBase = "http://127.0.0.1:$WebPort"
$resultFile = Join-Path $WebRoot "e2e_result.txt"
$reportDir = Join-Path $WebRoot "playwright-report"

function Test-UrlOk {
    param([string]$Url, [int]$TimeoutSec = 5)
    try {
        $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return $true
    } catch {
        return $false
    }
}

function Wait-For {
    param(
        [scriptblock]$Predicate,
        [int]$TimeoutSec,
        [string]$Label
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (& $Predicate) { return $true }
        Start-Sleep -Seconds 2
    }
    throw "Timeout waiting for $Label (${TimeoutSec}s)."
}

function Test-ApiHealth {
    if (-not (Test-UrlOk "$ApiBase/health")) { return $false }
    try {
        $body = Invoke-RestMethod -Uri "$ApiBase/health" -TimeoutSec 5
        return ($body.code -eq 0)
    } catch {
        return $false
    }
}

function Test-WebDev {
    Test-UrlOk $WebBase
}

function Test-LoginPreflight {
    try {
        $payload = @{ username = "admin"; password = "Admin@123" } | ConvertTo-Json
        $body = Invoke-RestMethod -Uri "$ApiBase/admin-api/ims/auth/login" -Method POST `
            -ContentType "application/json" -Body $payload -TimeoutSec 15
        return ($body.code -eq 0 -and $body.data.accessToken)
    } catch {
        return $false
    }
}

function Start-ImsApi {
    $dotenvScript = Join-Path $BackendRoot "scripts\_import_dotenv.ps1"
    if (Test-Path $dotenvScript) {
        . $dotenvScript
        $null = Import-ImsDotEnv -Path (Join-Path $BackendRoot ".env")
    }
    Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue |
        ForEach-Object { $_.OwningProcess } |
        Where-Object { $_ -and $_ -ne 0 } |
        Sort-Object -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    if (-not $env:IMS_COLLECTOR_BASE_URL) {
        $env:IMS_COLLECTOR_STUB = "1"
    }
    Start-Process -FilePath "python" -ArgumentList @("-m", "app.main") `
        -WorkingDirectory $BackendRoot -WindowStyle Hidden | Out-Null
}

function Start-ImsWebDev {
    # npm.cmd needs cmd.exe on Windows; pass IMS_API for Vite proxy.
    $env:IMS_API = $ApiBase
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "npm run dev") `
        -WorkingDirectory $WebRoot -WindowStyle Hidden | Out-Null
}

Write-Host "[e2e] Preflight API $ApiBase ..."
if (-not (Test-ApiHealth)) {
    if ($SkipServe) {
        throw "API not reachable at $ApiBase (use without -SkipServe to auto-start)."
    }
    Write-Host "[e2e] Starting API (KillPort + python -m app.main) ..."
    Start-ImsApi
    Wait-For -Predicate { Test-ApiHealth } -TimeoutSec $ApiWaitSec -Label "API health"
}

Write-Host "[e2e] Preflight Vite $WebBase ..."
if (-not (Test-WebDev)) {
    if ($SkipServe) {
        throw "Frontend not reachable at $WebBase (use without -SkipServe to auto-start)."
    }
    Write-Host "[e2e] Starting npm run dev ..."
    Start-ImsWebDev
    Wait-For -Predicate { Test-WebDev } -TimeoutSec $WebWaitSec -Label "Vite dev server"
}

Write-Host "[e2e] Login preflight (admin) ..."
if (-not (Test-LoginPreflight)) {
    Write-Warning @"
Login failed against $ApiBase.
Hint: from ims-backend run:  scripts\init_ims_db.ps1
Then restart API (scripts\start_api.ps1 -KillPort) and re-run this script.
"@
    "0 passed (login preflight failed — see init_ims_db.ps1)" | Set-Content -Path $resultFile -Encoding utf8
    exit 3
}

Write-Host "[e2e] Refresh workbench + acct pool + FIN live + cert + asset reverse + S1 fixtures + train overdue (#46/#47/#50/#55/#72/#73/#76) ..."
Push-Location $BackendRoot
try {
    python -c @"
from app.core import SessionLocal
from app.models import User
from app.workbench_seed import prune_closure_alert_inbox, refresh_workbench_e2e_seed
from app.acct_seed import clear_apply_number_gap, refresh_acct_e2e_pool
from app.live_fin_e2e_seed import refresh_live_fin_e2e_deps
from app.cert_e2e_seed import refresh_cert_e2e_seed
from app.asset_reverse_e2e_seed import refresh_asset_reverse_e2e_session
from app.s1_lifecycle_seed import ensure_s1_fixtures
from app.train_stat_e2e_seed import refresh_train_stat_e2e_seed
from app.kuaishou_collect_seed import refresh_kuaishou_collect_seed
from app.douyin_collect_seed import refresh_douyin_collect_seed
from app.perf_e2e_seed import refresh_perf_e2e_seed
db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == 'admin', User.deleted == 0).first()
    if admin is not None:
        refresh_workbench_e2e_seed(db, admin)
        prune_closure_alert_inbox(db)
        refresh_acct_e2e_pool(db, admin)
        refresh_live_fin_e2e_deps(db, admin)
        refresh_cert_e2e_seed(db, admin)
        refresh_asset_reverse_e2e_session(db, admin)
        ensure_s1_fixtures(db)
        clear_apply_number_gap(db)
        refresh_train_stat_e2e_seed(db, admin)
        refresh_kuaishou_collect_seed()
        refresh_douyin_collect_seed()
        refresh_perf_e2e_seed(db, admin)
        db.commit()
finally:
    db.close()
"@
} finally {
    Pop-Location
}

# Always align Playwright baseURL with Vite preflight port (ignore stale shell E2E_BASE_URL e.g. 5173).
if ($env:E2E_BASE_URL -and $env:E2E_BASE_URL -ne $WebBase) {
    Write-Warning "[e2e] Overriding E2E_BASE_URL=$($env:E2E_BASE_URL) -> $WebBase"
}
$env:E2E_BASE_URL = $WebBase
Write-Host "[e2e] E2E_BASE_URL=$env:E2E_BASE_URL"

$E2eWorkers = if ($env:IMS_E2E_WORKERS) { $env:IMS_E2E_WORKERS } else { "2" }
Write-Host "[e2e] Running Playwright (--workers=$E2eWorkers, HTML -> playwright-report/) ..."
$logPath = Join-Path $WebRoot "e2e_run.log"
if (Test-Path $logPath) {
    Remove-Item $logPath -Force -ErrorAction SilentlyContinue
}

Push-Location $WebRoot
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & npx playwright test --workers=$E2eWorkers --retries=1 --reporter=list,html 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 0 }
} finally {
    $ErrorActionPreference = $prevEap
    Pop-Location
}

$log = Get-Content -Path $logPath -Raw -ErrorAction SilentlyContinue
if (-not $log) { $log = "" }

$summaryLine = ($log -split "`n" | Where-Object { $_ -match '\d+\s+passed' } | Select-Object -Last 1)
if ($summaryLine -and $summaryLine -match '(\d+)\s+passed') {
    $passedLine = "$($Matches[1]) passed"
} else {
    $passedLine = "0 passed (no playwright summary — see e2e_run.log)"
}

@(
    "IMS E2E run $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "API: $ApiBase  Web: $WebBase"
    "ExitCode: $exitCode"
    "Report: $reportDir/index.html"
    "--- playwright list output (tail) ---"
    ($log -split "`n" | Select-Object -Last 30)
    "---"
    $passedLine
) | Set-Content -Path $resultFile -Encoding utf8

Write-Host "[e2e] $($passedLine)"
Write-Host "[e2e] Full log: $logPath"
Write-Host "[e2e] Summary: $resultFile"
if (Test-Path (Join-Path $reportDir "index.html")) {
    Write-Host "[e2e] HTML report: $(Join-Path $reportDir 'index.html')"
}

exit [int]$exitCode
