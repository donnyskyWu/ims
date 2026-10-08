@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
set "REPO_ROOT=%CD%"
rem PowerShell 启动 API：scripts\start_api.ps1（可选 -KillPort 释放 18080）

rem --- 跑前检测：禁止与并行 pytest / 多路测库进程同抢 ims_test（Win11 无 wmic）---
python "%~dp0_pytest_preflight.py"
if errorlevel 1 goto :preflight_fail
goto :preflight_ok
:preflight_fail
echo.
echo [run_pytest] 警告：检测到已有 pytest 或并行测库进程。
echo   请勿并行执行全量/模块测试，否则 MySQL 易出现 1684 1050 1062 等并发 DDL 错误。
echo   请先结束其它 pytest 或同目录 python 测库进程后再运行本脚本。
echo.
exit /b 1
:preflight_ok

if not exist "tests" mkdir tests
echo.> "tests\.pytest_full_run.lock"

if exist "tests\.ims_test_ddl.lock" del /f /q "tests\.ims_test_ddl.lock"
echo.
echo 若并行 pytest 导致 MySQL 1684，请先执行：
echo   DROP DATABASE ims_test; CREATE DATABASE ims_test CHARACTER SET utf8mb4;
echo   DROP DATABASE ims_ops_test; CREATE DATABASE ims_ops_test CHARACTER SET utf8mb4;
echo.
echo 单进程运行全量测试（重置测库 ^→ pytest_result.txt）...
python "%~dp0_reset_test_dbs.py"
if errorlevel 1 (
  set EXITCODE=!ERRORLEVEL!
  goto :done
)
python "%~dp0_run_pytest_to_file.py"
set EXITCODE=!ERRORLEVEL!
if exist "tests\.pytest_full_run.lock" del /f /q "tests\.pytest_full_run.lock"
:done
if exist "tests\.pytest_full_run.lock" del /f /q "tests\.pytest_full_run.lock"
endlocal & exit /b %EXITCODE%
