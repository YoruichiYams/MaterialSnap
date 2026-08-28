import sys
import ctypes
import os

def enable_hidpi_awareness():
    """
    Enables Windows Per-Monitor DPI awareness (V2 where supported)
    so screenshot coordinates and UI elements match real screen pixels.
    """
    if sys.platform != "win32":
        return

    # Enable Qt High-DPI scaling environment flags if needed
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    # Try Windows 10 Creator's Update+ Per-Monitor V2
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        set_dpi_context = ctypes.windll.user32.SetProcessDpiAwarenessContext
        set_dpi_context.argtypes = [ctypes.c_void_p]
        set_dpi_context.restype = ctypes.c_bool
        res = set_dpi_context(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        if res:
            return
    except Exception:
        pass

    # Try Windows 8.1+ SetProcessDpiAwareness
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    # Fallback Windows Vista+ SetProcessDPIAware
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
