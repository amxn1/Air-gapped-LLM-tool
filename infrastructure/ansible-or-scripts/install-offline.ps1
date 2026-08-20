<#
.SYNOPSIS
    Installs and launches the Offline LLM Assistant in an air-gapped Windows environment.
#>
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Starting Air-Gapped Offline LLM Assistant Deployment (Win)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Create required persistent data directories
Write-Host "[1/4] Creating local storage directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data\postgres", "data\qdrant", "data\storage", "models" | Out-Null

# 2. Check compose configuration
$ComposeDir = Join-Path $PSScriptRoot "..\compose"
$EnvFile = Join-Path $ComposeDir ".env"
$EnvExample = Join-Path $ComposeDir ".env.example"

if (-not (Test-Path $EnvFile) -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "[2/4] Initialized .env from .env.example" -ForegroundColor Green
} else {
    Write-Host "[2/4] Configuration .env verified" -ForegroundColor Green
}

# 3. Check Docker
Write-Host "[3/4] Checking Docker Compose..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Set-Location $ComposeDir
    docker compose up -d
} else {
    Write-Host "Docker command not found. You can run FastAPI and React locally with Python & Node." -ForegroundColor Yellow
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Deployment script finished." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
