Set-Location $PSScriptRoot\..
$log = Join-Path $PWD "pytest_spawn.log"
$env:PYTEST_ADDOPTS = ""
"start $(Get-Date -Format o)" | Out-File $log -Encoding utf8
python scripts\_pytest_preflight.py
"preflight exit $LASTEXITCODE" | Add-Content $log
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts\_reset_test_dbs.py
"reset exit $LASTEXITCODE" | Add-Content $log
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest -q --tb=line *> pytest_result.txt
"pytest exit $LASTEXITCODE" | Add-Content $log
exit $LASTEXITCODE
