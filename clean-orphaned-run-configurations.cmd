@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%SCRIPT_DIR%clean_orphaned_run_configurations.py" %*
    exit /b %ERRORLEVEL%
)
python "%SCRIPT_DIR%clean_orphaned_run_configurations.py" %*
exit /b %ERRORLEVEL%
