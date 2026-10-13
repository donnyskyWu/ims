# 启动 v2 API。从仓库 ims-backend/.env 读入 IMS_DINGTALK_*，不把密钥写进 v2 yaml。
$ErrorActionPreference = "Stop"
$Backend = Split-Path $PSScriptRoot -Parent
$Repo = Split-Path (Split-Path $Backend -Parent) -Parent
$DotEnv = Join-Path $Repo "ims-backend\.env"

if (Test-Path $DotEnv) {
    Get-Content $DotEnv | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        if ($val.Length -ge 2 -and (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'")))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        if ($key -and -not [Environment]::GetEnvironmentVariable($key, "Process")) {
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

$env:IMS_ENV = "dev"
Set-Location $Backend
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "缺少 $Python ，请先用 Python 3.10 创建 v2/ims-backend/.venv"
}
& $Python -m uvicorn app.main:app --factory --host 127.0.0.1 --port 18080
