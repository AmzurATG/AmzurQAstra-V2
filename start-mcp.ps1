# QAstra MCP Server Startup Script
Write-Host "Starting QAstra MCP Server on port 3001..." -ForegroundColor Green

Set-Location mcp-server

# Install dependencies if node_modules doesn't exist
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host "Installing Playwright browsers..." -ForegroundColor Yellow
    npx playwright install
}

# Run MCP server
npm run dev
