@echo off
cd /d "%~dp0"

set CMD=%1

if "%CMD%"=="start" goto start
if "%CMD%"=="stop" goto stop
if "%CMD%"=="" (
    echo Usage:
    echo   dev start    Start Django and Frontend dev servers
    echo   dev stop     Stop Django and Frontend dev servers
    echo.
    goto :EOF
)

:start
echo Starting Redis...
docker compose -f docker-compose.local.yml up -d 2>&1
echo.

echo Starting Django (port 8000)...
start "pyERP Django" cmd /k "uv run python manage.py runserver"

echo Starting Frontend (port 5173)...
start "pyERP Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers starting in separate windows.
echo Close windows or run "dev stop" to stop.
goto :EOF

:stop
echo Stopping Django...
call :kill_port 8000

echo Stopping Frontend...
call :kill_port 5173

echo Stopping Redis...
docker compose -f docker-compose.local.yml down 2>&1

echo Done.
goto :EOF

:kill_port
setlocal
set PORT=%1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% "') do (
    for /f "tokens=1" %%b in ("%%a") do (
        if not "%%b"=="0" (
            taskkill /PID %%b /f >nul 2>&1
        )
    )
)
endlocal
goto :EOF
