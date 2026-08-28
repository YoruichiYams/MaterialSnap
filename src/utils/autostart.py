import sys
import os
from pathlib import Path

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "MaterialSnap"

def _get_launch_command() -> str:
    """Returns the command to run MaterialSnap on Windows startup."""
    # If running as a standalone frozen executable (PyInstaller)
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    # If running from source
    main_py = Path(__file__).resolve().parent.parent.parent / "main.py"
    
    # If running with pythonw.exe, use pythonw so no console window opens
    python_exe = sys.executable
    if python_exe.lower().endswith("python.exe"):
        pythonw_candidate = python_exe[:-10] + "pythonw.exe"
        if os.path.exists(pythonw_candidate):
            python_exe = pythonw_candidate
            
    return f'"{python_exe}" "{main_py}"'

def is_autostart_enabled() -> bool:
    """Checks if MaterialSnap is registered in Windows Startup Registry."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            try:
                val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
                return bool(val)
            except FileNotFoundError:
                return False
    except Exception as e:
        print(f"[Autostart] Failed to read registry: {e}")
        return False

def set_autostart(enabled: bool) -> bool:
    """Enables or disables MaterialSnap in Windows Startup Registry."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE | winreg.KEY_WRITE) as key:
            if enabled:
                cmd = _get_launch_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                safe_cmd = cmd.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
                print(f"[Autostart] Enabled: {safe_cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                    print("[Autostart] Disabled")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[Autostart] Failed to update registry: {e}")
        return False
