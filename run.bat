@echo off
title Aegis Knowledge System - Launcher
echo ============================================================
echo Starting Aegis Knowledge System (Backend + Frontend)
echo ============================================================

cd /d "%~dp0backend"
echo [1/2] Launching Backend on port 8000...
start "Aegis Backend (FastAPI)" cmd /k "python -m uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

cd /d "%~dp0frontend"
echo [2/2] Launching Frontend on port 5173...
start "Aegis Frontend (Vite React)" cmd /k "npm run dev"

echo ============================================================
echo Both servers started!
echo Frontend will be accessible at: http://localhost:5173
echo Backend API Docs: http://localhost:8000/docs
echo ============================================================
timeout /t 5
