@echo off
setlocal

REM ============================================================
REM Research Webapp Starter
REM ============================================================

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_ROOT=%~dp0..\.."
set "APP_PATH=prototype\apps\research_webapp\app.py"
set "APP_PORT=8500"
set "APP_NAME=Research Webapp"

cd /d "%PROJECT_ROOT%"
if errorlevel 1 (
    echo [FEHLER] Projektverzeichnis konnte nicht geöffnet werden: %PROJECT_ROOT%
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden: .venv
    pause
    exit /b 1
)

if not exist "%APP_PATH%" (
    echo [FEHLER] Research Webapp nicht gefunden: %APP_PATH%
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo.
echo ============================================================
echo  Starte %APP_NAME%
echo ============================================================
echo Projektverzeichnis: %cd%
echo Port: %APP_PORT%
echo.
echo [INFO] Starte %APP_NAME% auf Port %APP_PORT%...
python -m streamlit run "%APP_PATH%" --server.port %APP_PORT%

pause
endlocal
