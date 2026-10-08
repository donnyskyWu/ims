# Repo-root orchestrator: delegate to ims-web one-command E2E (preflight + Playwright).
$ErrorActionPreference = "Stop"
$WebScript = Join-Path (Split-Path $PSScriptRoot -Parent) "..\ims-web\scripts\run_e2e.ps1"
$WebScript = (Resolve-Path $WebScript).Path
& $WebScript @args
exit $LASTEXITCODE
