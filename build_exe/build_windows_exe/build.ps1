# ============================================
#  QAstra Windows EXE Builder (PowerShell)
#  Run from build_exe\build_windows_exe\
#
#  Prerequisites:
#    - Python 3.11+ installed and on PATH
#    - Node.js 18+ / npm installed and on PATH
# ============================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$VenvPath = Join-Path $ProjectRoot "venv"

Write-Host "============================================"
Write-Host " QAstra Windows EXE Builder"
Write-Host "============================================"
Write-Host ""

# [1/6] Virtual environment
if (Test-Path $VenvPath) {
    Write-Host "[1/6] Virtual environment found, activating..."
} else {
    Write-Host "[1/6] Creating virtual environment..."
    py -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: py -m venv"; exit 1 }
}
& (Join-Path $VenvPath "Scripts\Activate.ps1")
Write-Host "       Python: $(python --version) @ $(Get-Command python | Select-Object -ExpandProperty Source)"

# [2/6] Frontend dependencies
Write-Host "[2/6] Installing frontend dependencies..."
Set-Location (Join-Path $ProjectRoot "frontend")
npm install
if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: npm install"; exit 1 }

# [3/6] Build React
Write-Host "[3/6] Building React frontend..."
npm run build
if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: npm run build"; exit 1 }

# [4/6] Python dependencies
Write-Host "[4/6] Installing Python dependencies..."
Set-Location $ProjectRoot
pip install -r backend/requirements.txt
pip install pyinstaller
if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: pip install"; exit 1 }

# [5/6] PyInstaller
Write-Host "[5/6] Building exe with PyInstaller..."
Set-Location $ScriptDir
$DistPath = Join-Path $ScriptDir "dist"
$BuildPath = Join-Path $ScriptDir "build"
pyinstaller qastra.spec --clean --distpath $DistPath --workpath $BuildPath
if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: pyinstaller"; exit 1 }

# [6/6] Copy .env template
Write-Host "[6/6] Copying .env template..."
Copy-Item -Path (Join-Path $ScriptDir ".env.template") -Destination (Join-Path $DistPath ".env") -Force

Write-Host ""
Write-Host "============================================"
Write-Host " Build complete!"
Write-Host " Output: build_exe\build_windows_exe\dist\QAstra.exe"
Write-Host " Reminder: ensure .env is configured next"
Write-Host " to QAstra.exe before running."
Write-Host "============================================"
