@echo off
title MaterialSnap Launcher
cd /d "%~dp0"

echo [MaterialSnap] Checking dependencies...
python -m pip install -r requirements.txt

echo [MaterialSnap] Launching MaterialSnap...
start pythonw main.py
echo [MaterialSnap] Started in background tray mode! Press Ctrl+Shift+S or PrintScreen to capture.
