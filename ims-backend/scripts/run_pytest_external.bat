@echo off
rem Run outside Cursor if the integrated shell kills long pytest (~30 min).
rem 1) Stop stray pytest only (NOT the API on 18080):
rem    powershell -NoProfile -Command "Get-CimInstance Win32_Process ^| Where-Object { $_.CommandLine -match '-m pytest' } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
rem 2) Start API if needed: powershell -File "%~dp0start_api.ps1" [-KillPort]
rem 3) Full suite (single process):
cd /d "%~dp0.."
call "%~dp0run_pytest.cmd"
echo Exit code: %ERRORLEVEL%
echo Result file: %CD%\pytest_result.txt
pause
