import threading
import time
import sys
from PySide6.QtCore import QObject, Signal
import pynput.keyboard

class HotkeyListener(QObject):
    """
    Listens for global hotkeys in the background without blocking the UI.
    Emits `sig_triggered` (cross-thread safe via Qt signal/slot mechanism).
    Includes thread-safe debounce protection against rapid key-repeat spam.
    """
    sig_triggered = Signal()

    def __init__(self, hotkey_str: str = "Ctrl+Shift+S", parent=None):
        super().__init__(parent)
        self.hotkey_str = hotkey_str or "Ctrl+Shift+S"
        self._listener = None
        self._stop_event = threading.Event()
        self._thread = None
        self._last_trigger_time = 0.0
        self._lock = threading.Lock()

    def _normalize_hotkey(self, combo: str) -> str:
        """Converts user-friendly combo strings to pynput format."""
        if not combo:
            return "<ctrl>+<shift>+s"
        combo = combo.replace(" ", "")
        parts = combo.split("+")
        pynput_parts = []
        for part in parts:
            p = part.lower()
            if p in ["ctrl", "control"]:
                pynput_parts.append("<ctrl>")
            elif p in ["shift"]:
                pynput_parts.append("<shift>")
            elif p in ["alt"]:
                pynput_parts.append("<alt>")
            elif p in ["win", "windows", "cmd"]:
                pynput_parts.append("<cmd>")
            elif p in ["printscreen", "prtscr", "prtsc", "snapshot"]:
                pynput_parts.append("<print_screen>")
            elif p in ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]:
                pynput_parts.append(f"<{p}>")
            else:
                pynput_parts.append(p)
        return "+".join(pynput_parts)

    def start(self):
        """Starts background hotkey listening with fallback protection."""
        self.stop()
        self._stop_event.clear()

        def run_listener():
            try:
                # Build hotkey mapping
                mapping = {}
                primary = self._normalize_hotkey(self.hotkey_str)
                try:
                    mapping[primary] = self._on_triggered
                except Exception:
                    mapping["<ctrl>+<shift>+s"] = self._on_triggered

                # Also support <print_screen> by default
                if primary != "<print_screen>":
                    mapping["<print_screen>"] = self._on_triggered

                if primary != "<ctrl>+<shift>+s":
                    mapping["<ctrl>+<shift>+s"] = self._on_triggered

                with pynput.keyboard.GlobalHotKeys(mapping) as h:
                    self._listener = h
                    h.join()
            except Exception as e:
                print(f"[HotkeyListener] Error in hotkey hook: {e}")
                # Fallback to standard PrintScreen only if primary combination had syntax errors
                try:
                    with pynput.keyboard.GlobalHotKeys({"<print_screen>": self._on_triggered}) as fallback_h:
                        self._listener = fallback_h
                        fallback_h.join()
                except Exception as ex2:
                    print(f"[HotkeyListener] Fallback hook failed: {ex2}")

        self._thread = threading.Thread(target=run_listener, daemon=True, name="HotkeyThread")
        self._thread.start()

    def _on_triggered(self):
        """Dispatches signal safely to Qt main thread with debounce protection."""
        now = time.time()
        with self._lock:
            if now - self._last_trigger_time < 0.30:  # 300ms debounce
                return
            self._last_trigger_time = now
        self.sig_triggered.emit()

    def update_hotkey(self, new_hotkey_str: str):
        """Updates the active hotkey and restarts listener."""
        self.hotkey_str = new_hotkey_str or "Ctrl+Shift+S"
        self.start()

    def stop(self):
        """Stops background hotkey listener cleanly."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
