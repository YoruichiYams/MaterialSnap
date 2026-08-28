import os
import re
import sys
import subprocess
from pathlib import Path

# Reserved Windows file names
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

# Forbidden Windows path characters
INVALID_CHARS_REGEX = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def _safe_log(msg: str):
    """Safely prints log messages preventing Windows console encoding crashes."""
    try:
        enc = sys.stdout.encoding or "utf-8"
        clean_msg = msg.encode(enc, errors="replace").decode(enc)
        print(clean_msg)
    except Exception:
        pass

def get_default_screenshots_dir() -> Path:
    """Returns the default safe screenshots directory on user's system."""
    try:
        pictures = Path.home() / "Pictures" / "Screenshots"
        pictures.mkdir(parents=True, exist_ok=True)
        return pictures
    except Exception:
        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        return desktop

def sanitize_filename(filename: str, fallback: str = "Screenshot.png") -> str:
    r"""
    Sanitizes a filename to prevent path traversal (CWE-22) and Windows invalid character crashes.
    Removes traversal patterns (../, ..\), null bytes, invalid chars, and checks reserved names.
    """
    if not filename or not isinstance(filename, str):
        return fallback

    # Strip null bytes and control chars
    clean = filename.replace("\x00", "").strip()

    # Extract strictly the basename (strip any directory parts)
    clean = os.path.basename(clean)

    # Remove illegal Windows characters
    clean = INVALID_CHARS_REGEX.sub("_", clean)

    # Strip leading/trailing dots and whitespace
    clean = clean.strip(". ")

    if not clean:
        return fallback

    # Check Windows reserved base names
    stem = clean.split(".")[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        clean = f"_{clean}"

    # Enforce safe length limit (max 200 chars)
    if len(clean) > 200:
        ext = Path(clean).suffix
        clean = clean[:190] + ext

    return clean

def validate_save_directory(directory_path: str, fallback_to_default: bool = True) -> Path:
    """
    Validates and normalizes a save directory path.
    Prevents path traversal, checks write permissions, and falls back safely if inaccessible.
    """
    if not directory_path or not isinstance(directory_path, str):
        return get_default_screenshots_dir() if fallback_to_default else Path.home()

    # Strip null bytes and trailing quotes/spaces
    clean_dir = directory_path.replace("\x00", "").strip(" \"'")

    try:
        p = Path(clean_dir).resolve()
        
        # Check if path contains invalid colon usage (only allowed as drive letter like C:\)
        drive, rest = os.path.splitdrive(str(p))
        if ":" in rest:
            raise ValueError(f"Invalid colon in path: {p}")

        # Attempt directory creation and write probe
        p.mkdir(parents=True, exist_ok=True)
        
        # Test write permission with temporary probe file
        test_file = p / f".tmp_write_probe_{os.getpid()}"
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("probe")
            test_file.unlink(missing_ok=True)
        except Exception as perm_err:
            raise PermissionError(f"Directory not writable: {p} ({perm_err})")

        return p
    except Exception as e:
        _safe_log(f"[PathSecurity] Directory '{directory_path}' invalid or unwritable ({e}).")
        if fallback_to_default:
            return get_default_screenshots_dir()
        raise

def safe_open_folder(folder_path: str) -> bool:
    """
    Safely opens a folder in Windows Explorer without risk of arbitrary executable launch (CWE-78 / CWE-88).
    Strictly verifies that target is an existing directory before invocation.
    """
    if not folder_path or not isinstance(folder_path, str):
        return False

    clean_path = folder_path.replace("\x00", "").strip(" \"'")
    try:
        target = Path(clean_path).resolve()
        if not target.exists() or not target.is_dir():
            _safe_log(f"[PathSecurity] Refusing to open non-directory target: {target}")
            return False

        if sys.platform == "win32":
            # Launch explorer.exe specifically with directory target, no shell interpretation
            subprocess.Popen(["explorer.exe", str(target)], shell=False)
            return True
        else:
            return False
    except Exception as e:
        _safe_log(f"[PathSecurity] Error safely opening folder: {e}")
        return False
