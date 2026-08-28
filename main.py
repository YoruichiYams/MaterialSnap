import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.dpi import enable_hidpi_awareness

# Enable DPI awareness BEFORE Qt Application initialization
enable_hidpi_awareness()

from PySide6.QtCore import Qt, QObject, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from src.config.config_manager import ConfigManager
from src.capture.capture_engine import CaptureEngine
from src.ui.styles import COLORS
from src.ui.icon_generator import IconGenerator
from src.ui.overlay import ScreenshotOverlay
from src.ui.tray_manager import TrayManager
from src.utils.hotkey_listener import HotkeyListener
from src.ui.toast import show_quick_toast

SINGLE_INSTANCE_SERVER_NAME = "MaterialSnap_SingleInstance_IPC_Server"

class MaterialSnapApp(QObject):
    """
    Main Controller coordinating capture, overlay, hotkeys, and system tray.
    """
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.app.setQuitOnLastWindowClosed(False)

        # 1. Config Manager
        self.config_manager = ConfigManager()
        self._is_capturing = False

        # 2. UI Components
        self.overlay = ScreenshotOverlay(self.config_manager)
        self.tray = TrayManager(self.config_manager)

        # 3. Hotkey Listener
        active_hotkey = self.config_manager.get("hotkey", "Ctrl+Shift+S")
        self.hotkey_listener = HotkeyListener(active_hotkey)
        self.hotkey_listener.sig_triggered.connect(self.trigger_capture, Qt.QueuedConnection)
        self.hotkey_listener.start()

        # Connect Tray signals
        self.tray.sig_capture_requested.connect(self.trigger_capture)
        self.tray.sig_hotkey_changed.connect(self.hotkey_listener.update_hotkey)
        self.tray.sig_settings_updated.connect(self.overlay.reload_config)

        # Ensure assets directory and icon exist
        self._ensure_app_assets()

    def _ensure_app_assets(self):
        """Generates and saves the application icon to assets/."""
        assets_dir = BASE_DIR / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        icon_path = assets_dir / "app_icon.png"
        icon_pix = IconGenerator.create_app_icon(128).pixmap(128, 128)
        icon_pix.save(str(icon_path), "PNG")

    @Slot()
    def trigger_capture(self):
        """Captures all screens and launches the frozen overlay with reentrancy guard."""
        # Reentrancy & visibility lock
        if self._is_capturing or (self.overlay and self.overlay.isVisible()):
            return

        self._is_capturing = True
        try:
            # Instant screen grab across all monitors
            composite_pixmap, virtual_rect = CaptureEngine.capture_all_screens()
            
            # Display frozen overlay
            self.overlay.start_capture(composite_pixmap, virtual_rect)
        finally:
            self._is_capturing = False

    def cleanup(self):
        """Gracefully release resources on exit."""
        self.hotkey_listener.stop()
        if self.overlay:
            self.overlay.close()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MaterialSnap")
    app.setOrganizationName("MaterialSnap")

    # Set Window Icon
    app_icon = IconGenerator.create_app_icon(64)
    app.setWindowIcon(app_icon)

    # Single-instance IPC Guard
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_SERVER_NAME)
    if socket.waitForConnected(500):
        # Already running: trigger screenshot in running instance
        socket.write(b"TRIGGER_CAPTURE")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)

    # Start IPC server for single instance control
    server = QLocalServer()
    server.removeServer(SINGLE_INSTANCE_SERVER_NAME)
    server.listen(SINGLE_INSTANCE_SERVER_NAME)

    controller = MaterialSnapApp(app)

    def handle_incoming_ipc():
        client = server.nextPendingConnection()
        if client:
            client.waitForReadyRead(500)
            # Read max 256 bytes to prevent socket flooding
            raw_bytes = client.read(256).data()
            msg = raw_bytes.decode("utf-8", errors="ignore")
            if "TRIGGER_CAPTURE" in msg:
                controller.trigger_capture()
            client.disconnectFromServer()

    server.newConnection.connect(handle_incoming_ipc)

    # Initial launch toast
    active_hk = controller.config_manager.get("hotkey", "Ctrl+Shift+S")
    show_quick_toast(f"MaterialSnap running in background • Press {active_hk}", icon_type="app")

    exit_code = app.exec()
    controller.cleanup()
    server.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
