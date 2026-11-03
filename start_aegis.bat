@echo off
title Aegis Knowledge System (Unified Server)
cd /d "%~dp0backend"
echo ============================================================
echo   Starting Aegis System (Full-Stack on http://localhost:8000)
echo ============================================================
echo   - Web UI Dashboard: http://localhost:8000
echo   - Interactive API Docs: http://localhost:8000/docs
echo ============================================================
echo.
"C:\Program Files\Python313\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
