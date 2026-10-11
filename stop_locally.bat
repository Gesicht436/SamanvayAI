@echo off
setlocal enabledelayedexpansion

title Samanvay Platform Stopper

echo ======================================================================
echo    Stopping Samanvay Local Services
echo ======================================================================
echo.

echo Terminating Backend and Frontend processes...
taskkill /FI "WINDOWTITLE eq Samanvay Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Samanvay Frontend*" /T /F >nul 2>&1

echo Services stopped.
echo.
set /p STOP_DOCKER="Do you also want to stop the PostgreSQL Docker container? (y/N): "
if /i "%STOP_DOCKER%"=="y" (
    docker compose stop db
    echo Database container stopped.
)

echo Done.
pause
