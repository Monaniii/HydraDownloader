# Development launcher for Hydra Downloader.
# Starts the backend and the Angular dev server, then launches Electron.

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$electronDir = Join-Path $root "electron"

Write-Host "=== Hydra Downloader | Dev Mode ===" -ForegroundColor Cyan

# 1. Start backend
Write-Host "Starting FastAPI backend..." -ForegroundColor Yellow
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}
$backend = Start-Process -FilePath $python `
    -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000","--reload" `
    -WorkingDirectory $backendDir `
    -PassThru -WindowStyle Hidden

# 2. Start Angular dev server
Write-Host "Starting Angular dev server..." -ForegroundColor Yellow
$frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "start" `
    -WorkingDirectory $frontendDir `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 8

# 3. Launch Electron
Write-Host "Launching Electron..." -ForegroundColor Yellow
Set-Location $electronDir
npm start

# Cleanup on exit
Write-Host "Cleaning up processes..." -ForegroundColor Yellow
Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
