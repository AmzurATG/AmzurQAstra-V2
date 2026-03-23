# QAstra Frontend Startup Script
Write-Host "Starting QAstra Frontend on port 5173..." -ForegroundColor Green

Set-Location frontend

# Install dependencies if node_modules doesn't exist
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Run Vite dev server
npm run dev
