Set-Location $PSScriptRoot\..
$env:PYTEST_ADDOPTS = ""
$p = Start-Process python -ArgumentList @("scripts\_run_pytest_to_file.py") -WorkingDirectory $PWD -PassThru -Wait -NoNewWindow
Write-Host "pytest wrapper exit $($p.ExitCode)"
Get-Content pytest_result.txt -Tail 5 -ErrorAction SilentlyContinue
exit $p.ExitCode
