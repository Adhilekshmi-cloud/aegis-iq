@echo off
cd /d "%~dp0backend"
echo ============================================================
echo Starting Aegis Backend on http://127.0.0.1:8000
echo ============================================================
"C:\Program Files\Python313\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
