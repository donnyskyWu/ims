Set-Location $PSScriptRoot\..
$p = Start-Process cmd.exe -ArgumentList @(
  '/c', 'scripts\run_pytest.cmd > full_run.log 2>&1'
) -WorkingDirectory $PWD -PassThru -Wait -NoNewWindow
Write-Host "cmd exit $($p.ExitCode)"
Get-Content full_run.log -Tail 15 -ErrorAction SilentlyContinue
if (Test-Path pytest_result.txt) {
  Get-Content pytest_result.txt -Tail 5
}
exit $p.ExitCode
