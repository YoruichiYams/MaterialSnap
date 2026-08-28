import os
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from .styles import FONT_FAMILY, COLORS
from .icon_generator import IconGenerator
from .settings_dialog import SettingsDialog
from ..utils.autostart import is_autostart_enabled, set_autostart

class TrayManager(QObject):
    """
    Manages the Windows System Tray Icon, context menu, and background lifecycle
    with strict monochromatic neutral dark-gray aesthetic.
    """
    sig_capture_requested = Signal()
    sig_hotkey_changed = Signal(str)
    sig_settings_updated = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.tray_icon = None
        self.tray_menu = None
        self.settings_dialog = None

        self._init_tray()

    def _init_tray(self):
        # Generate monochromatic icon
        app_icon = IconGenerator.create_app_icon(32)

        self.tray_icon = QSystemTrayIcon(app_icon, self)
        self.tray_icon.setToolTip("MaterialSnap — Screenshot Utility")

        # Build Context Menu
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['menu_bg']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 6px;
                font-family: {FONT_FAMILY};
                font-size: 13px;
                font-weight: 500;
            }}
            QMenu::item {{
                padding: 8px 24px 8px 14px;
                border-radius: 8px;
            }}
            QMenu::item:selected {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS['menu_separator']};
                margin: 4px 8px;
            }}
        """)

        # Capture Action
        hk = self.config_manager.get("hotkey", "Ctrl+Shift+S")
        self.action_capture = QAction(f"Capture Screenshot ({hk})", self)
        self.action_capture.setIcon(IconGenerator.create_copy_icon(18, "#FFFFFF"))
        self.action_capture.triggered.connect(self.sig_capture_requested.emit)
        self.tray_menu.addAction(self.action_capture)

        # Open Folder Action
        self.action_folder = QAction("Open Screenshots Folder", self)
        self.action_folder.setIcon(IconGenerator.create_folder_icon(18, "#FFFFFF"))
        self.action_folder.triggered.connect(self._open_screenshots_folder)
        self.tray_menu.addAction(self.action_folder)

        self.tray_menu.addSeparator()

        # Checkable: Auto-copy to Clipboard
        self.action_auto_copy = QAction("Auto-copy to Clipboard", self, checkable=True)
        self.action_auto_copy.setChecked(self.config_manager.get("auto_copy_clipboard", True))
        self.action_auto_copy.toggled.connect(self._toggle_auto_copy)
        self.tray_menu.addAction(self.action_auto_copy)

        # Checkable: Autostart on Windows Boot
        self.action_autostart = QAction("Start on Windows Boot", self, checkable=True)
        self.action_autostart.setChecked(is_autostart_enabled())
        self.action_autostart.toggled.connect(self._toggle_autostart)
        self.tray_menu.addAction(self.action_autostart)

        self.tray_menu.addSeparator()

        # Settings Dialog Action
        self.action_settings = QAction("Settings...", self)
        self.action_settings.triggered.connect(self._open_settings)
        self.tray_menu.addAction(self.action_settings)

        self.tray_menu.addSeparator()

        # Exit Action
        self.action_exit = QAction("Exit MaterialSnap", self)
        self.action_exit.triggered.connect(QApplication.quit)
        self.tray_menu.addAction(self.action_exit)

        self.tray_icon.setContextMenu(self.tray_menu)
        
        # Left click on tray icon triggers capture
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger: # Single click
            self.sig_capture_requested.emit()

    def _open_screenshots_folder(self):
        folder = self.config_manager.get("save_directory", str(Path.home() / "Pictures" / "Screenshots"))
        Path(folder).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception as e:
            print(f"[Tray] Error opening folder: {e}")

    def _toggle_auto_copy(self, checked: bool):
        self.config_manager.set("auto_copy_clipboard", checked)

    def _toggle_autostart(self, checked: bool):
        set_autostart(checked)
        self.config_manager.set("autostart", checked)

    def _open_settings(self):
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self.config_manager)
            self.settings_dialog.sig_settings_updated.connect(self._on_settings_saved)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _on_settings_saved(self):
        # Refresh hotkey text and menu states
        hk = self.config_manager.get("hotkey", "Ctrl+Shift+S")
        self.action_capture.setText(f"Capture Screenshot ({hk})")
        self.action_auto_copy.setChecked(self.config_manager.get("auto_copy_clipboard", True))
        self.action_autostart.setChecked(is_autostart_enabled())
        self.sig_hotkey_changed.emit(hk)
        self.sig_settings_updated.emit()
