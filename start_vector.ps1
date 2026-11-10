# VECTOR Autonomous Launch Script
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  VECTOR: Autonomous Web Operator" -ForegroundColor Yellow
Write-Host "  Starting Backend and Frontend Servers..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$root = $PSScriptRoot
if (-not $root) { $root = Get-Location }

# Start Backend in new PowerShell window
Write-Host "[1/3] Launching FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$root'; python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 2

# Start Frontend in new PowerShell window
Write-Host "[2/3] Launching Vite Frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 3

# Open Default Web Browser
Write-Host "[3/3] Opening Browser at http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host "Servers launched in dedicated terminal windows! Keep them open while testing." -ForegroundColor Cyan

