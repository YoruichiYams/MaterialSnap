import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Force offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.dpi import enable_hidpi_awareness
enable_hidpi_awareness()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QPoint, Qt
from PySide6.QtGui import QPixmap
from src.config.config_manager import ConfigManager
from src.config.themes import WAVE_THEMES, DEFAULT_WAVE_THEME, get_wave_palette
from src.ui.styles import COLORS, PILL_STYLE, TOAST_STYLE, SETTINGS_DIALOG_STYLE
from src.ui.icon_generator import IconGenerator
from src.ui.toast import ToastWidget, show_quick_toast
from src.ui.action_pill import ActionPillWidget
from src.ui.overlay import ScreenshotOverlay
from src.ui.settings_dialog import SettingsDialog
from src.ui.tray_manager import TrayManager
from src.ui.fluid_mesh import FluidMeshGradient
from src.capture.capture_engine import CaptureEngine
from src.utils.autostart import is_autostart_enabled, set_autostart
from src.utils.hotkey_listener import HotkeyListener
from src.utils.path_security import sanitize_filename, validate_save_directory, safe_open_folder

class TestMaterialSnapFullSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_monochromatic_styles_and_colors(self):
        # Monochromatic neutral dark-gray tokens
        self.assertIn("bg_canvas", COLORS)
        self.assertEqual(COLORS["bg_canvas"], "#161719")
        self.assertEqual(COLORS["surface_card"], "#232529")
        self.assertEqual(COLORS["surface_input"], "#1A1B1E")
        self.assertEqual(COLORS["btn_primary_bg"], "#FFFFFF")
        self.assertEqual(COLORS["btn_primary_fg"], "#161719")
        self.assertEqual(COLORS["toast_bg"], "rgba(22, 23, 25, 0.94)")

        # Verify zero blue colors in core styles
        self.assertNotIn("#8AB4F8", SETTINGS_DIALOG_STYLE)
        self.assertNotIn("#4285F4", SETTINGS_DIALOG_STYLE)
        self.assertNotIn("#8AB4F8", TOAST_STYLE)

        self.assertTrue(len(PILL_STYLE) > 0)
        self.assertTrue(len(TOAST_STYLE) > 0)

    def test_wave_theme_palettes_and_fallback(self):
        # Verify all 6 themes exist and have 4 hex colors
        expected_themes = [
            "Twilight Mauve", "Nordic Frost", "Neon Sunset",
            "Forest Mist", "Pastel Pop", "Deep Ocean"
        ]
        for theme_name in expected_themes:
            self.assertIn(theme_name, WAVE_THEMES)
            palette = get_wave_palette(theme_name)
            self.assertEqual(len(palette), 4)
            for hex_code in palette:
                self.assertTrue(hex_code.startswith("#"))
                self.assertEqual(len(hex_code), 7)

        # Fallback handling
        fallback_palette = get_wave_palette("NonExistentTheme_12345")
        self.assertEqual(fallback_palette, WAVE_THEMES[DEFAULT_WAVE_THEME])

        # ConfigManager integration
        cm = ConfigManager()
        self.assertEqual(cm.get("wave_theme"), DEFAULT_WAVE_THEME)

        # Setting and getting a valid theme
        cm.set("wave_theme", "Neon Sunset")
        self.assertEqual(cm.get("wave_theme"), "Neon Sunset")

        # FluidMeshGradient theme update
        fluid = FluidMeshGradient(theme_name="Forest Mist")
        self.assertEqual(fluid._theme_name, "Forest Mist")
        fluid.set_theme("Deep Ocean")
        self.assertEqual(fluid._theme_name, "Deep Ocean")

    def test_icon_generator(self):
        icon = IconGenerator.create_app_icon(64)
        self.assertFalse(icon.isNull())
        
        copy_icon = IconGenerator.create_copy_icon(24)
        self.assertFalse(copy_icon.isNull())

        save_icon = IconGenerator.create_save_icon(24)
        self.assertFalse(save_icon.isNull())

        check_icon = IconGenerator.create_check_icon(24)
        self.assertFalse(check_icon.isNull())

        folder_icon = IconGenerator.create_folder_icon(24)
        self.assertFalse(folder_icon.isNull())

    def test_action_pill_widget(self):
        pill = ActionPillWidget()
        self.assertIsNotNone(pill.btn_copy)
        self.assertIsNotNone(pill.btn_save)
        self.assertIsNotNone(pill.btn_cancel)

        # Test smart positioning
        selection = QRect(100, 100, 400, 300)
        bounds = QRect(0, 0, 1920, 1080)
        pill.position_smartly(selection, bounds)
        self.assertTrue(pill.pos().x() >= bounds.left())
        self.assertTrue(pill.pos().y() >= bounds.top())

    def test_toast_subsystem_events(self):
        # 1. Startup toast
        t1 = show_quick_toast("MaterialSnap running in background • Press Ctrl+Shift+S", icon_type="app")
        self.assertIsNotNone(t1)
        self.assertEqual(t1.msg_label.text(), "MaterialSnap running in background • Press Ctrl+Shift+S")

        # 2. Copied toast
        t2 = show_quick_toast("Screenshot copied to clipboard", icon_type="copy")
        self.assertIsNotNone(t2)
        self.assertEqual(t2.msg_label.text(), "Screenshot copied to clipboard")

        # 3. Saved toast with folder action
        t3 = show_quick_toast("Saved to Screenshots • Click to open", folder_to_open=str(BASE_DIR), icon_type="folder")
        self.assertIsNotNone(t3)
        self.assertIn("Saved to Screenshots", t3.msg_label.text())

    def test_overlay_creation_and_memory_cleanup(self):
        cm = ConfigManager()
        overlay = ScreenshotOverlay(cm)
        self.assertIsNotNone(overlay.header_badge)
        self.assertIsNotNone(overlay.action_pill)

        # Test start capture with dummy pixmap
        dummy = QPixmap(1920, 1080)
        dummy.fill(Qt.white)
        v_rect = QRect(-1920, 0, 3840, 1080) # Multi-monitor with negative left
        overlay.start_capture(dummy, v_rect)

        self.assertFalse(overlay.bg_pixmap.isNull())
        self.assertEqual(overlay.geometry(), v_rect)

        # Test memory deallocation on close
        overlay.close_overlay()
        self.assertTrue(overlay.bg_pixmap.isNull())
        self.assertFalse(overlay.has_selection)

    def test_save_fallback_on_invalid_directory(self):
        test_cfg = BASE_DIR / "temp_test_cfg.json"
        cm = ConfigManager(str(test_cfg))
        # Set impossible path on Windows
        cm.set("save_directory", "Z:\\NonExistentDrive_12345\\Folder")
        overlay = ScreenshotOverlay(cm)
        
        dummy = QPixmap(100, 100)
        dummy.fill(Qt.white)
        overlay.bg_pixmap = dummy
        overlay.has_selection = True
        overlay.selection_rect = QRect(0, 0, 50, 50)

        # Should not raise exception, but fallback safely
        overlay._do_save(prompt_custom_folder=False)
        self.assertTrue(overlay.bg_pixmap.isNull())
        if test_cfg.exists():
            test_cfg.unlink()

    def test_settings_dialog(self):
        cm = ConfigManager()
        dlg = SettingsDialog(cm)
        self.assertTrue(dlg.edit_dir.text() != "")
        self.assertTrue(dlg.edit_hotkey.text() != "")
        self.assertTrue(dlg.chk_show_title.isChecked())
        self.assertTrue(dlg.chk_fluid_wave.isChecked())
        self.assertTrue(dlg.combo_wave_theme.count() >= 6)

        # Test custom checkbox toggling
        state = dlg.chk_show_title.isChecked()
        dlg.chk_show_title.setChecked(not state)
        self.assertEqual(dlg.chk_show_title.isChecked(), not state)

    def test_tray_manager(self):
        cm = ConfigManager()
        tray = TrayManager(cm)
        self.assertIsNotNone(tray.tray_icon)
        self.assertIsNotNone(tray.tray_menu)
        self.assertTrue(len(tray.tray_menu.actions()) > 0)

    def test_autostart_toggle(self):
        curr = is_autostart_enabled()
        set_autostart(not curr)
        self.assertEqual(is_autostart_enabled(), not curr)
        set_autostart(curr)
        self.assertEqual(is_autostart_enabled(), curr)

    def test_hotkey_listener_normalization(self):
        listener = HotkeyListener("Ctrl + Shift + S")
        self.assertEqual(listener._normalize_hotkey("Ctrl + Shift + S"), "<ctrl>+<shift>+s")
        self.assertEqual(listener._normalize_hotkey("PrintScreen"), "<print_screen>")
        self.assertEqual(listener._normalize_hotkey("Alt+F10"), "<alt>+<f10>")
        self.assertEqual(listener._normalize_hotkey(""), "<ctrl>+<shift>+s")

    # Security & Stress Tests
    def test_path_traversal_sanitization(self):
        self.assertEqual(sanitize_filename("../../etc/passwd.png"), "passwd.png")
        self.assertEqual(sanitize_filename("..\\..\\Windows\\System32\\cmd.exe"), "cmd.exe")
        self.assertEqual(sanitize_filename("image\x00.png"), "image.png")
        self.assertEqual(sanitize_filename('bad:file*name?.png'), "bad_file_name_.png")
        self.assertEqual(sanitize_filename("CON.png"), "_CON.png")
        self.assertEqual(sanitize_filename("NUL.jpg"), "_NUL.jpg")
        self.assertEqual(sanitize_filename("aux.txt"), "_aux.txt")

    def test_validate_save_directory_security(self):
        d1 = validate_save_directory("")
        self.assertTrue(d1.exists())
        d2 = validate_save_directory("X:\\ImpossibleDrive\\NonExistentFolder_9999")
        self.assertTrue(d2.exists())
        temp_dir = BASE_DIR / "temp_valid_dir_test"
        d3 = validate_save_directory(str(temp_dir))
        self.assertTrue(d3.exists())
        temp_dir.rmdir()

    def test_safe_open_folder_blocks_arbitrary_files(self):
        self.assertFalse(safe_open_folder("Z:\\FakeFolder_12345"))
        test_file = BASE_DIR / "temp_test_executable.bat"
        with open(test_file, "w") as f:
            f.write("echo test")
        self.assertFalse(safe_open_folder(str(test_file)))
        test_file.unlink()

    def test_hotkey_listener_debounce(self):
        listener = HotkeyListener()
        emitted_count = 0
        def on_emit():
            nonlocal emitted_count
            emitted_count += 1
        listener.sig_triggered.connect(on_emit)

        for _ in range(5):
            listener._on_triggered()

        self.assertEqual(emitted_count, 1)

    def test_capture_engine_filename_sanitization(self):
        filename = CaptureEngine.generate_filename("C:\\ValidDir", prefix="../../hacked_prefix", ext="..\\exe")
        self.assertTrue(".." not in filename)
        self.assertTrue("hacked_prefix" in filename)

if __name__ == "__main__":
    unittest.main()
