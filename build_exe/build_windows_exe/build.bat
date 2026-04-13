@echo off
REM ============================================
REM  QAstra Windows EXE Builder
REM  Run this script from build_exe\build_windows_exe\
REM ============================================

REM Navigate to project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
set "BUILD_DIR=%SCRIPT_DIR%"

echo ============================================
echo  QAstra Windows EXE Builder
echo ============================================
echo.

echo [1/5] Installing frontend dependencies...
cd /d "%PROJECT_ROOT%frontend"
call npm install
if errorlevel 1 (echo FAILED: npm install & pause & exit /b 1)

echo [2/5] Building React frontend...
call npm run build
if errorlevel 1 (echo FAILED: npm run build & pause & exit /b 1)

echo [3/5] Installing Python dependencies...
cd /d "%PROJECT_ROOT%"
pip install -r backend/requirements.txt
pip install pyinstaller
if errorlevel 1 (echo FAILED: pip install & pause & exit /b 1)

echo [4/5] Building exe with PyInstaller...
cd /d "%BUILD_DIR%"
pyinstaller qastra.spec --clean --distpath "%BUILD_DIR%dist" --workpath "%BUILD_DIR%build"
if errorlevel 1 (echo FAILED: pyinstaller & pause & exit /b 1)

echo [5/5] Copying .env template...
copy /Y "%BUILD_DIR%.env.template" "%BUILD_DIR%dist\.env" >nul 2>&1

echo.
echo ============================================
echo  Build complete!
echo  Output: build_exe\build_windows_exe\dist\QAstra.exe
echo  Reminder: ensure .env is configured next
echo  to QAstra.exe before running.
echo ============================================
pause
