@echo off
echo ===================================================================
echo     STARTING ENTERPRISE MULTI-AGENT DEMO (BACKEND + FRONTEND)
echo ===================================================================
echo.

REM 1. Start FastAPI Backend on port 8000
echo [1/2] Starting FastAPI Backend on http://localhost:8000 ...
start "SupportShield API" cmd /k "cd /d "%~dp0\.." && .\venv\Scripts\python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload --reload-dir api --reload-dir core --reload-dir agents"

REM 2. Wait a moment for backend to initialize
timeout /t 3 /nobreak > nul

REM 3. Start React + Vite Frontend on port 5173
echo [2/2] Starting React + Vite Frontend on http://localhost:5173 ...
start "SupportShield UI" cmd /k "cd /d "%~dp0\..\frontend" && npm run dev"

echo.
echo ===================================================================
echo Both services launched!
echo - API Backend:  http://localhost:8000
echo - Swagger Docs: http://localhost:8000/docs
echo - Frontend UI:  http://localhost:5173
echo ===================================================================
