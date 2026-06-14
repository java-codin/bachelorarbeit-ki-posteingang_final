@echo off
setlocal

REM ============================================================
REM Research Webapp Starter
REM ============================================================

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "TARGET_SCRIPT=start_research_webapp.bat"

if not exist "%SCRIPT_DIR%%TARGET_SCRIPT%" (
    echo [FEHLER] Zielskript nicht gefunden: %SCRIPT_DIR%%TARGET_SCRIPT%
    pause
    exit /b 1
)

call "%SCRIPT_DIR%%TARGET_SCRIPT%"
set "SCRIPT_EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %SCRIPT_EXIT_CODE%
