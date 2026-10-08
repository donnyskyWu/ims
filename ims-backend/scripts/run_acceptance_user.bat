@echo off
rem IMS user acceptance — run each step in an EXTERNAL cmd (not Cursor integrated shell).
echo.
echo [1/3] Services: API 18080 + frontend 6173
echo   powershell -NoProfile -File "%~dp0start_api.ps1" [-KillPort]
echo   cd ..\..\ims-web ^&^& npm run dev
echo   curl http://127.0.0.1:18080/health  ^&  open http://127.0.0.1:6173
echo.
echo [2/3] pytest full suite (single process, ~30 min) — NOT in Cursor:
echo   "%~dp0run_pytest_external.bat"
echo   Read last line of: ims-backend\pytest_result.txt
echo.
echo [3/3] Playwright smoke S1-S12:
echo   cd ims-web ^&^& npx playwright install chromium ^&^& npm run test:e2e
echo   Expect: 12 passed
echo.
pause
