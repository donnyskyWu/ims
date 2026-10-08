# Pull org directory from DingTalk and upsert IMS mappings (R1 admin).
param(
    [string]$BaseUrl = "http://127.0.0.1:18080",
    [string]$Username = "admin",
    [string]$Password = "Admin@123"
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/admin-api/ims/auth/login" `
    -ContentType "application/json" `
    -Body (@{ username = $Username; password = $Password } | ConvertTo-Json)
if ($login.code -ne 0) {
    throw "login failed: $($login.msg)"
}
$token = $login.data.accessToken
$headers = @{ Authorization = "Bearer $token" }

$sync = Invoke-RestMethod -Method Post -Uri "$BaseUrl/admin-api/ims/auth/org/sync-from-dingtalk" `
    -Headers $headers -ContentType "application/json" -Body "{}"
$outFile = Join-Path $PSScriptRoot "..\dingtalk_sync_result.txt"
$lines = @(
    "sync-from-dingtalk at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "code=$($sync.code) msg=$($sync.msg)",
    ($sync | ConvertTo-Json -Depth 6)
)
$data = $sync.data
if ($null -ne $data) {
    $userTotal = [int]$data.usersCreated + [int]$data.usersUpdated
    $hint = $data.authScopeHint
    $partial = [bool]$data.partialScope
    if (
        -not $hint -and $sync.code -eq 0 -and [int]$data.departmentsFetched -le 1 -and $userTotal -le 10
    ) {
        $partial = $true
        $roots = ($data.authorizedRootDeptIds | ForEach-Object { "$_" }) -join ","
        $hint = "Sync OK but narrow scope: departments=$($data.departmentsFetched) users=$userTotal authorizedRootDeptIds=$roots. Set DingTalk contact auth scope to all employees, republish app, rerun this script."
    }
    if ($partial -or $hint) {
        $lines += "PO hint:"
        if ($partial) { $lines += "partialScope=true" }
        if ($hint) { $lines += "authScopeHint=$hint" }
    }
}
$lines | Set-Content -Path $outFile -Encoding utf8
Write-Host ($sync | ConvertTo-Json -Depth 6)
if ($sync.code -ne 0) { exit 1 }
