# ============================================
#  QAstra Windows EXE Builder (PowerShell)
#  Run from build_exe\build_windows_exe\
#
#  Prerequisites (do these BEFORE running this script):
#    1. Python 3.11+ installed and on PATH
#    2. Node.js 18+ / npm installed and on PATH
#    3. Create & activate virtual environment:
#         cd <project_root>
#         python -m venv venv
#         .\venv\Scripts\Activate.ps1
#    4. Install Python dependencies:
#         pip install -r backend/requirements.txt
#         pip install pyinstaller
#    5. Install frontend dependencies:
#         cd frontend
#         npm install
#         cd ..
# ============================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")

Write-Host "============================================"
Write-Host " QAstra Windows EXE Builder"
Write-Host "============================================"
Write-Host ""

# ── Preflight checks ────────────────────────────────────────
# Verify virtual environment is active
if (-not $env:VIRTUAL_ENV) {
    Write-Error "No virtual environment detected. Activate your venv first:`n  .\venv\Scripts\Activate.ps1"
    exit 1
}
Write-Host "[OK] Virtual environment: $env:VIRTUAL_ENV"

# Verify pyinstaller is installed
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "PyInstaller not found. Run: pip install pyinstaller"
    exit 1
}
Write-Host "[OK] PyInstaller: $(pyinstaller --version)"

# Verify node_modules exist
$NodeModules = Join-Path $ProjectRoot "frontend\node_modules"
if (-not (Test-Path $NodeModules)) {
    Write-Error "frontend/node_modules not found. Run: cd frontend && npm install"
    exit 1
}
Write-Host "[OK] Frontend node_modules found"
Write-Host ""

# ── Clean previous build artifacts ──────────────────────────
$DistPath = Join-Path $ScriptDir "dist"
$BuildPath = Join-Path $ScriptDir "build"
foreach ($dir in @($DistPath, $BuildPath)) {
    if (Test-Path $dir) {
        Write-Host "Cleaning $dir ..."
        # Remove contents, not the directory itself (avoids lock from Explorer)
        Get-ChildItem -Path $dir -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# [1/4] Build React
Write-Host "[1/4] Building React frontend..."
Set-Location (Join-Path $ProjectRoot "frontend")
npm run build
if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: npm run build"; exit 1 }

# [2/4] PyInstaller
Write-Host "[2/4] Building exe with PyInstaller..."
Set-Location $ScriptDir
pyinstaller qastra.spec --clean --distpath $DistPath --workpath $BuildPath
if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: pyinstaller"; exit 1 }

# [3/4] Copy .env template
Write-Host "[3/4] Copying .env template..."
Copy-Item -Path (Join-Path $ScriptDir ".env.template") -Destination (Join-Path $DistPath ".env") -Force

# [4/4] Summary
$ExePath = Join-Path $DistPath "QAstra.exe"
$ExeSize = if (Test-Path $ExePath) { "{0:N1} MB" -f ((Get-Item $ExePath).Length / 1MB) } else { "not found" }

Write-Host ""
Write-Host "============================================"
Write-Host " Build complete!"
Write-Host " Output: $ExePath"
Write-Host " Size:   $ExeSize"
Write-Host ""
Write-Host " To distribute, copy these together:"
Write-Host "   - dist\QAstra.exe"
Write-Host "   - dist\.env  (user must configure)"
Write-Host "============================================"
