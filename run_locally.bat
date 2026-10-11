@echo off
setlocal enabledelayedexpansion

title Samanvay Platform Launcher

echo ======================================================================
echo    SAMANVAY - Unified Material Master Harmonization Platform
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Check Prerequisites
echo [1/5] Checking prerequisites...

:: Check uv
uv --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 'uv' is not installed or not in PATH.
    echo Please install Astral uv: https://astral.sh/uv
    pause
    exit /b 1
)
echo  [x] Astral uv found.

:: Check Node.js
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 'node' is not installed or not in PATH.
    echo Please install Node.js 18+: https://nodejs.org
    pause
    exit /b 1
)
echo  [x] Node.js found.

:: Check Docker & Start Database
docker --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [!] Docker not found in PATH. Assuming external PostgreSQL at localhost:5432...
) else (
    echo  [x] Docker found. Ensuring PostgreSQL container is running...
    docker compose up -d db >nul 2>&1
)

:: 2. Database Migrations
echo.
echo [2/5] Applying Alembic schema migrations...
uv run alembic upgrade head
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Database migration failed. Is PostgreSQL running on localhost:5432?
    pause
    exit /b 1
)
echo  [x] Database schema up to date.

:: 3. Seed Reference Clusters
echo.
echo [3/5] Seeding reference clusters and financial baselines...
uv run python -m scripts.seed_clusters
echo  [x] Reference clusters verified.

:: 4. Launch Backend API Server (FastAPI :8000)
echo.
echo [4/5] Launching Backend API server (FastAPI on http://localhost:8000)...
start "Samanvay Backend (Port 8000)" cmd /k "title Samanvay Backend && cd /d "%~dp0" && uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

:: 5. Launch Frontend Web UI (Next.js :3000)
echo.
echo [5/5] Launching Frontend Web server (Next.js on http://localhost:3000)...
start "Samanvay Frontend (Port 3000)" cmd /k "title Samanvay Frontend && cd /d "%~dp0web" && npm run dev"

:: Wait 3 seconds and launch browser
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo ======================================================================
echo    Samanvay is now running!
echo ======================================================================
echo.
echo    - Frontend Dashboard:  http://localhost:3000
echo    - API Interactive Docs: http://localhost:8000/docs
echo    - System Health Check:  http://localhost:8000/health
echo.
echo    Log outputs are visible in their respective dedicated terminal windows.
echo    To stop all services, close both terminal windows or run stop_locally.bat.
echo ======================================================================
echo.
pause
