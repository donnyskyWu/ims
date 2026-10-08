Set-Location $PSScriptRoot\..
$env:PYTEST_ADDOPTS = ""
$p = Start-Process -FilePath python -ArgumentList @("scripts\_run_pytest_to_file.py") -WorkingDirectory $PWD -PassThru -Wait -NoNewWindow
exit $p.ExitCode
