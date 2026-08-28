@echo off
title MaterialSnap Standalone Builder
cd /d "%~dp0"

echo ======================================================
echo    MaterialSnap - Standalone Windows .EXE Builder
echo ======================================================
echo.

echo [0/3] Stopping any running MaterialSnap instances...
taskkill /F /IM MaterialSnap.exe >nul 2>&1

echo [1/3] Ensuring icon asset is generated...
python scripts/generate_ico.py

echo [2/3] Checking PyInstaller...
python -m pip install pyinstaller

echo [3/3] Packaging standalone executable with PyInstaller...
python -m PyInstaller --clean MaterialSnap.spec

echo.
if exist "dist\MaterialSnap.exe" (
    echo ======================================================
    echo  [SUCCESS] Build complete!
    echo  Executable created at: dist\MaterialSnap.exe
    echo ======================================================
) else (
    echo ======================================================
    echo  [ERROR] Build failed. Please check the log above.
    echo ======================================================
)
