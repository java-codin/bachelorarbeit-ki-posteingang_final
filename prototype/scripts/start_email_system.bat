@echo off
setlocal

REM ============================================================
REM E-Mail-Gesamtsystem Starter
REM ============================================================

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_ROOT=%~dp0..\.."
set "WORKER_PATH=prototype\apps\core\mail\email_worker_mailpit.py"
set "OPERATIONS_APP_PATH=prototype\apps\operations_dashboard\app.py"
set "MAIL_SIMULATOR_APP_PATH=prototype\apps\mail_simulator\app.py"
set "TEAM_REVIEW_APP_PATH=prototype\apps\team_review\app.py"

set "SYSTEM_NAME=E-Mail-Gesamtsystem"
set "WORKER_NAME=Mailpit Worker"
set "OPERATIONS_APP_NAME=Operations Dashboard"
set "MAIL_SIMULATOR_APP_NAME=Bürger-Mail-Simulator"
set "TEAM_REVIEW_APP_NAME=Fachteam-Freigabe"

set "MAILPIT_URL=http://localhost:8025"
set "OPERATIONS_PORT=8501"
set "MAIL_SIMULATOR_PORT=8502"
set "TEAM_REVIEW_PORT=8503"

cd /d "%PROJECT_ROOT%"
if errorlevel 1 (
    echo [FEHLER] Projektverzeichnis konnte nicht geöffnet werden: %PROJECT_ROOT%
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Starte %SYSTEM_NAME%
echo ============================================================
echo Projektverzeichnis: %cd%
echo Operations-Port: %OPERATIONS_PORT%
echo Simulator-Port: %MAIL_SIMULATOR_PORT%
echo Fachteam-Port: %TEAM_REVIEW_PORT%
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden: .venv
    pause
    exit /b 1
)

if not exist "%WORKER_PATH%" (
    echo [FEHLER] Mailpit Worker nicht gefunden: %WORKER_PATH%
    pause
    exit /b 1
)

if not exist "%OPERATIONS_APP_PATH%" (
    echo [FEHLER] Operations Dashboard nicht gefunden: %OPERATIONS_APP_PATH%
    pause
    exit /b 1
)

if not exist "%MAIL_SIMULATOR_APP_PATH%" (
    echo [FEHLER] Bürger-Mail-Simulator nicht gefunden: %MAIL_SIMULATOR_APP_PATH%
    pause
    exit /b 1
)

if not exist "%TEAM_REVIEW_APP_PATH%" (
    echo [FEHLER] Fachteam-Freigabe nicht gefunden: %TEAM_REVIEW_APP_PATH%
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo [INFO] Starte Docker Compose...
docker compose up -d

if errorlevel 1 (
    echo [FEHLER] Docker Compose konnte nicht gestartet werden.
    pause
    exit /b 1
)

echo [INFO] Starte %WORKER_NAME%...
start "Mailpit Worker" cmd /k call ".venv\Scripts\activate.bat" ^&^& python "%WORKER_PATH%"

echo [INFO] Starte %MAIL_SIMULATOR_APP_NAME% auf Port %MAIL_SIMULATOR_PORT%...
start "Bürger Mail Simulator" cmd /k call ".venv\Scripts\activate.bat" ^&^& python -m streamlit run "%MAIL_SIMULATOR_APP_PATH%" --server.port %MAIL_SIMULATOR_PORT%

echo [INFO] Starte %TEAM_REVIEW_APP_NAME% auf Port %TEAM_REVIEW_PORT%...
start "Fachteam Freigabe" cmd /k call ".venv\Scripts\activate.bat" ^&^& python -m streamlit run "%TEAM_REVIEW_APP_PATH%" --server.port %TEAM_REVIEW_PORT%

echo [INFO] Öffne Mailpit...
start "" "%MAILPIT_URL%"

echo.
echo [INFO] Starte %OPERATIONS_APP_NAME% auf Port %OPERATIONS_PORT%...
echo [HINWEIS] Zum Beenden dieses Fenster mit STRG+C stoppen.
echo Danach werden Worker, Simulator, Fachteam-App und Docker Compose automatisch beendet.
echo.

python -m streamlit run "%OPERATIONS_APP_PATH%" --server.port %OPERATIONS_PORT%

echo.
echo ============================================================
echo  Beende Komponenten
echo ============================================================

echo [INFO] Beende %WORKER_NAME%...
taskkill /FI "WINDOWTITLE eq Mailpit Worker*" /T /F >nul 2>&1

echo [INFO] Beende %MAIL_SIMULATOR_APP_NAME%...
taskkill /FI "WINDOWTITLE eq Bürger Mail Simulator*" /T /F >nul 2>&1

echo [INFO] Beende %TEAM_REVIEW_APP_NAME%...
taskkill /FI "WINDOWTITLE eq Fachteam Freigabe*" /T /F >nul 2>&1

echo [INFO] Beende Docker Compose...
docker compose down

echo.
echo [INFO] %SYSTEM_NAME% wurde beendet.
echo.

pause
endlocal
