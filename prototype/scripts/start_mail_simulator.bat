@echo off
setlocal

REM ============================================================
REM Bürger-Mail-Simulator Starter
REM ============================================================

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_ROOT=%~dp0..\.."
set "APP_PATH=prototype\apps\mail_simulator\app.py"
set "APP_PORT=8502"
set "APP_NAME=Bürger-Mail-Simulator"

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
    echo [FEHLER] Bürger-Mail-Simulator nicht gefunden: %APP_PATH%
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
