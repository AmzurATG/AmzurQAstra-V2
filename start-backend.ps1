# QAstra Backend Startup Script
Write-Host "Starting QAstra Backend on port 8000..." -ForegroundColor Green

Set-Location backend

# Activate virtual environment if exists, otherwise create it
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    py -m venv venv
    & .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
}

# Run uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
