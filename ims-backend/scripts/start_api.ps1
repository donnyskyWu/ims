# Start IMS API (PowerShell-safe; avoid chaining with &&).
param(
    [switch]$KillPort
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
. (Join-Path $PSScriptRoot "_import_dotenv.ps1")
$null = Import-ImsDotEnv -Path (Join-Path (Get-Location).Path ".env")

if ($KillPort) {
    $port = if ($env:IMS_PORT) { [int]$env:IMS_PORT } else { 18080 }
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object { $_.OwningProcess } |
        Where-Object { $_ -and $_ -ne 0 } |
        Sort-Object -Unique |
        ForEach-Object {
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
}

python -m app.main
