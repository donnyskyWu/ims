# 本地 ims -> 云 MySQL ims（mysqldump | mysql）。密码仅来自环境变量，勿写入仓库。
param(
    [string]$DumpPath = (Join-Path (Join-Path $PSScriptRoot "..") "_ims_cloud_sync.dump.sql")
)

$ErrorActionPreference = "Stop"
$BackendRoot = Join-Path $PSScriptRoot ".."
. (Join-Path $PSScriptRoot "_import_dotenv.ps1")
$null = Import-ImsDotEnv -Path (Join-Path $BackendRoot ".env")

$localUser = if ($env:IMS_MYSQL_USER) { $env:IMS_MYSQL_USER } else { "root" }
$localPass = if ($env:IMS_MYSQL_PASSWORD) { $env:IMS_MYSQL_PASSWORD } else { "root" }
$localHost = if ($env:IMS_MYSQL_HOST) { $env:IMS_MYSQL_HOST } else { "127.0.0.1" }
$localPort = if ($env:IMS_MYSQL_PORT) { $env:IMS_MYSQL_PORT } else { "3306" }
$localDb = if ($env:IMS_DB) { $env:IMS_DB } else { "ims" }

$remoteHost = if ($env:IMS_CLOUD_MYSQL_HOST) { $env:IMS_CLOUD_MYSQL_HOST } else { "47.110.62.216" }
$remotePort = if ($env:IMS_CLOUD_MYSQL_PORT) { $env:IMS_CLOUD_MYSQL_PORT } else { "3306" }
$remoteUser = if ($env:IMS_CLOUD_MYSQL_USER) { $env:IMS_CLOUD_MYSQL_USER } else { "shenyu" }
$remotePass = $env:IMS_CLOUD_MYSQL_PASSWORD
if (-not $remotePass) {
    Write-Error "Set IMS_CLOUD_MYSQL_PASSWORD in the shell or ims-backend/.env (not committed)."
}

$mysql = Get-Command mysql -ErrorAction SilentlyContinue
$dump = Get-Command mysqldump -ErrorAction SilentlyContinue
if (-not $mysql -or -not $dump) {
    Write-Error "mysql/mysqldump not on PATH (install MySQL client tools)."
}

Write-Host "[sync] Dump local $localDb @ ${localHost}:${localPort} ..."
cmd /c "`"$($dump.Source)`" -u$localUser -p$localPass --host=$localHost --port=$localPort --single-transaction --routines --triggers --set-gtid-purged=OFF --default-character-set=utf8mb4 $localDb > `"$DumpPath`" 2>nul"
if ($LASTEXITCODE -ne 0) { throw "mysqldump failed (exit $LASTEXITCODE)" }

Write-Host "[sync] Ensure remote database ims (utf8mb4) ..."
& $mysql.Source -u$remoteUser -p"$remotePass" --host=$remoteHost --port=$remotePort -e `
    "CREATE DATABASE IF NOT EXISTS ``ims`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

Write-Host "[sync] Import to ${remoteHost}:${remotePort}/ims ..."
cmd /c "`"$($mysql.Source)`" -u$remoteUser -p$remotePass --host=$remoteHost --port=$remotePort --default-character-set=utf8mb4 ims < `"$DumpPath`" 2>nul"
if ($LASTEXITCODE -ne 0) { throw "mysql import failed (exit $LASTEXITCODE)" }

$tbl = & $mysql.Source -u$remoteUser -p"$remotePass" --host=$remoteHost --port=$remotePort -N -e `
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='ims';"
Write-Host "[sync] Remote table count: $tbl"
Remove-Item $DumpPath -Force -ErrorAction SilentlyContinue
Write-Host "[sync] Done (temp dump removed)."
