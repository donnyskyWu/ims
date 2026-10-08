# 一次性：从本地 ims-backend/.env 写入系统参数（勿提交 .env / 真实密钥）
# 用法：在 ims-backend 目录执行 .\scripts\seed_dingtalk_params_from_env.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Error "Missing $envFile — copy .env.local.example to .env and fill PO secrets locally."
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim().Trim('"')
        Set-Item -Path "env:$name" -Value $val
    }
}

Push-Location $root
try {
    python (Join-Path $PSScriptRoot "seed_dingtalk_params_from_env.py")
} finally {
    Pop-Location
}

Write-Host "Done. Prefer 系统管理 → 系统参数 for ongoing changes (no git)."
