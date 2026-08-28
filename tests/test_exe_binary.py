import subprocess
import time
import sys
import os
from pathlib import Path
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
exe_path = BASE_DIR / "dist" / "MaterialSnap.exe"

print("[Binary Test] Testing standalone MaterialSnap.exe...")
if not exe_path.exists():
    print("[Binary Test] ERROR: Executable not found in dist/")
    sys.exit(1)

# Ensure no old process is running before test
os.system("taskkill /F /IM MaterialSnap.exe >nul 2>&1")
time.sleep(1)

# Launch executable
subprocess.Popen([str(exe_path)])
print("[Binary Test] Launched MaterialSnap.exe")

# Wait for process initialization
time.sleep(3)

# Test Single-Instance IPC communication
app = QApplication.instance() or QApplication(sys.argv)
socket = QLocalSocket()
socket.connectToServer("MaterialSnap_SingleInstance_IPC_Server")
connected = socket.waitForConnected(3000)

if not connected:
    print("[Binary Test] ERROR: Could not connect to MaterialSnap IPC server!")
    os.system("taskkill /F /IM MaterialSnap.exe >nul 2>&1")
    sys.exit(1)

print("[Binary Test] IPC server connection SUCCESS! Sending test TRIGGER_CAPTURE packet...")
socket.write(b"TRIGGER_CAPTURE")
socket.waitForBytesWritten(1000)
socket.disconnectFromServer()
print("[Binary Test] IPC trigger sent successfully.")

# Clean up test process
print("[Binary Test] Cleaning up test process...")
os.system("taskkill /F /IM MaterialSnap.exe >nul 2>&1")
print("[Binary Test] Standalone executable verification PASSED!")
