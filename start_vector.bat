@echo off
title VECTOR Launch Controller
echo ===================================================
echo   VECTOR: Autonomous Web Operator
echo   Starting Backend and Frontend Dev Servers...
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/3] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "VECTOR - Backend (Port 8000)" cmd /k "python run_backend.py"

timeout /t 2 /nobreak >nul

echo [2/3] Launching Vite Frontend on http://localhost:5173 ...
start "VECTOR - Frontend (Port 5173)" cmd /k "cd frontend && npm run dev"

timeout /t 3 /nobreak >nul

echo [3/3] Opening Web Interface...
start http://localhost:5173

echo.
echo ===================================================
echo   VECTOR is running!
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://localhost:5173
echo.
echo   Keep the two server terminal windows open while using VECTOR.
echo   To stop VECTOR, simply close the server windows.
echo ===================================================
timeout /t 5
