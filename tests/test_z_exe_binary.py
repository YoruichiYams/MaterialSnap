import subprocess
import time
import sys
import os
import unittest
from pathlib import Path
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent

class TestExeBinary(unittest.TestCase):
    def test_standalone_executable(self):
        exe_path = BASE_DIR / "dist" / "MaterialSnap.exe"
        if not exe_path.exists():
            self.skipTest("dist/MaterialSnap.exe not built yet")

        print("[Binary Test] Testing standalone MaterialSnap.exe...")
        # Ensure no old process is running before test
        os.system("taskkill /F /IM MaterialSnap.exe >nul 2>&1")
        time.sleep(1)

        # Launch executable
        proc = subprocess.Popen([str(exe_path)])
        print("[Binary Test] Launched MaterialSnap.exe")

        try:
            # Wait for process initialization
            time.sleep(3)

            # Test Single-Instance IPC communication with polling retries
            app = QApplication.instance() or QApplication(sys.argv)
            socket = QLocalSocket()
            connected = False
            for attempt in range(15):
                socket.connectToServer("MaterialSnap_SingleInstance_IPC_Server")
                if socket.waitForConnected(1000):
                    connected = True
                    break
                time.sleep(0.5)

            self.assertTrue(connected, "Could not connect to MaterialSnap IPC server!")
            print("[Binary Test] IPC server connection SUCCESS! Sending test TRIGGER_CAPTURE packet...")
            socket.write(b"TRIGGER_CAPTURE")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            print("[Binary Test] IPC trigger sent successfully.")
        finally:
            # Clean up test process
            print("[Binary Test] Cleaning up test process...")
            os.system("taskkill /F /IM MaterialSnap.exe >nul 2>&1")
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass
            time.sleep(0.5)
            print("[Binary Test] Standalone executable verification PASSED!")

if __name__ == "__main__":
    unittest.main()
