@echo off
cd /d "d:\self\sy\IMS????\ims-backend"
python scripts\_reset_test_dbs.py
if errorlevel 1 exit /b 1
python -m pytest -q --tb=line > pytest_result.txt 2>&1
exit /b %ERRORLEVEL%
