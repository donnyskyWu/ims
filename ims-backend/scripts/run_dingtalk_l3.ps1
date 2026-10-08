# L3 钉钉组织联调：加载 ims-backend/.env，跑 pytest L3 + 可选 Playwright（不在 test:e2e:ci 内）
param(
    [switch]$SkipPlaywright,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$BackendRoot = Join-Path $PSScriptRoot ".."
$WebRoot = Join-Path (Split-Path $BackendRoot -Parent) "ims-web"
$EnvFile = Join-Path $BackendRoot ".env"

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Write-Warning "No .env at $Path — copy .env.local.example to .env and fill credentials."
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        if ($val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length - 2) }
        [Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
}

Import-DotEnv -Path $EnvFile
$env:IMS_DINGTALK_L3 = "1"

$exit = 0
if (-not $SkipPytest) {
    Write-Host "[L3] pytest tests/test_org_dingtalk_l3.py ..."
    Push-Location $BackendRoot
    try {
        python -m pytest -q tests/test_org_dingtalk_l3.py
        if ($LASTEXITCODE -ne 0) { $exit = [int]$LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

if (-not $SkipPlaywright) {
    $spec = Join-Path $WebRoot "e2e/dingtalk-org-l3.spec.ts"
    if (Test-Path $spec) {
        Write-Host "[L3] Playwright $spec ..."
        Push-Location $WebRoot
        try {
            $env:IMS_DINGTALK_L3 = "1"
            & npx playwright test e2e/dingtalk-org-l3.spec.ts --workers=1
            if ($LASTEXITCODE -ne 0 -and $exit -eq 0) { $exit = [int]$LASTEXITCODE }
        } finally {
            Pop-Location
        }
    }
}

exit $exit
