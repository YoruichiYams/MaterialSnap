import sys
import unittest
import tempfile
import json
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QColor, QPainter, QImage
from PySide6.QtWidgets import QApplication

from src.config.config_manager import ConfigManager
from src.ui.theme_toggle import ThemeToggle
from src.ui.styles import (
    THEME_TOKENS, get_theme_tokens, get_application_stylesheet,
    get_menu_style, get_pill_style, get_toast_style, get_settings_dialog_style
)
from src.ui.settings_dialog import SettingsDialog
from src.ui.tray_manager import TrayManager
from src.ui.action_pill import ActionPillWidget
from src.ui.toast import ToastWidget, ToastManager
from src.ui.overlay import ScreenshotOverlay

class TestThemeSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cfg_path = Path(self.temp_dir.name) / "config.json"
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump({"theme": "dark", "hotkey": "Ctrl+Shift+S"}, f)
        self.cfg = ConfigManager(str(self.cfg_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_theme_toggle_metrics_and_states(self):
        toggle = ThemeToggle(initial_theme="dark")
        self.assertEqual(toggle.width(), 64)
        self.assertEqual(toggle.height(), 32)
        self.assertTrue(toggle.is_dark())
        self.assertAlmostEqual(toggle.thumb_x, 4.0)

        # Paint dark state offscreen
        img = QImage(64, 32, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        toggle.paintEvent(None)
        p.end()

        # Toggle to light
        signals = []
        toggle.sig_theme_changed.connect(signals.append)
        toggle.toggle()
        self.assertFalse(toggle.is_dark())
        self.assertEqual(signals, ["light"])
        self.assertEqual(toggle._anim.duration(), 220)

        # Paint light state offscreen
        toggle.set_is_dark(False, animate=False)
        self.assertAlmostEqual(toggle.thumb_x, 36.0)
        img2 = QImage(64, 32, QImage.Format.Format_ARGB32_Premultiplied)
        img2.fill(0)
        p2 = QPainter(img2)
        toggle.paintEvent(None)
        p2.end()

    def test_theme_tokens_completeness(self):
        required_keys = [
            "surface_bg", "surface_card", "surface_hover",
            "border_subtle", "border_focus", "text_primary",
            "text_secondary", "text_muted", "button_bg",
            "button_hover", "button_pressed", "shadow_color",
            "scrim_overlay"
        ]
        for theme_name in ("dark", "light"):
            tokens = get_theme_tokens(theme_name)
            for k in required_keys:
                self.assertIn(k, tokens, f"Missing token '{k}' in theme '{theme_name}'")

        # Verify contrast specs
        dark = get_theme_tokens("dark")
        light = get_theme_tokens("light")
        self.assertEqual(dark["surface_bg"], "#121316")
        self.assertEqual(dark["surface_card"], "#161719")
        self.assertEqual(light["surface_bg"], "#FBFBFB")
        self.assertEqual(light["surface_card"], "#FFFFFF")

    def test_settings_dialog_theme_switching(self):
        dlg = SettingsDialog(self.cfg)
        self.assertIsNotNone(dlg.theme_toggle)
        self.assertTrue(dlg.theme_toggle.is_dark())

        # Verify 32px height standard on all controls
        self.assertEqual(dlg.edit_dir.height(), 32)
        self.assertEqual(dlg.btn_browse.height(), 32)
        self.assertEqual(dlg.edit_hotkey.height(), 32)
        self.assertEqual(dlg.combo_wave_theme.height(), 32)
        self.assertEqual(dlg.seg_texture_mode.height(), 32)
        self.assertEqual(dlg.btn_cancel.height(), 32)
        self.assertEqual(dlg.btn_save.height(), 32)

        # Toggle to light theme
        settings_signals = []
        dlg.sig_settings_updated.connect(lambda: settings_signals.append(True))
        dlg.theme_toggle.toggle()

        self.assertEqual(len(settings_signals), 1)
        self.assertFalse(dlg.theme_toggle.is_dark())
        self.assertEqual(self.cfg.get("theme"), "light")
        self.assertEqual(dlg._current_theme, "light")

        # Toggle back to dark theme
        dlg.theme_toggle.toggle()
        self.assertEqual(len(settings_signals), 2)
        self.assertTrue(dlg.theme_toggle.is_dark())
        self.assertEqual(self.cfg.get("theme"), "dark")

        # Verify all 4 themes in combobox
        theme_items = [dlg.combo_wave_theme.itemText(i) for i in range(dlg.combo_wave_theme.count())]
        self.assertEqual(theme_items, ["Samsung Aura", "Prism Spectrum", "Solar Flare", "Opal Nebula"])

        # Switch wave theme live
        dlg.combo_wave_theme.setCurrentText("Prism Spectrum")
        self.assertEqual(len(settings_signals), 3)
        self.assertEqual(self.cfg.get("wave_theme"), "Prism Spectrum")

        # Switch texture mode live
        dlg.seg_texture_mode.set_mode("Mesh")
        self.assertEqual(len(settings_signals), 4)
        self.assertEqual(self.cfg.get("wave_texture_mode"), "Mesh")

    def test_tray_menu_theme_adaptation(self):
        tray = TrayManager(self.cfg)
        self.assertIsNotNone(tray.tray_menu)
        
        # Test theme switching
        tray.set_theme("light")
        self.assertEqual(tray._current_theme, "light")
        tray.set_theme("dark")
        self.assertEqual(tray._current_theme, "dark")
        tray.tray_icon.hide()

    def test_action_pill_theme(self):
        pill = ActionPillWidget()
        pill.set_theme("light")
        self.assertEqual(pill._theme, "light")
        pill.set_theme("dark")
        self.assertEqual(pill._theme, "dark")

    def test_toast_theme_rendering(self):
        toast_dark = ToastWidget("Dark Toast", theme="dark")
        self.assertEqual(toast_dark._theme, "dark")
        toast_light = ToastWidget("Light Toast", theme="light")
        self.assertEqual(toast_light._theme, "light")

        # Offscreen paint of frames
        img = QImage(200, 38, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        toast_dark.frame.paintEvent(None)
        toast_light.frame.paintEvent(None)
        p.end()

    def test_overlay_scrim_theme_colors(self):
        overlay = ScreenshotOverlay(self.cfg)
        overlay.reload_config()
        self.assertEqual(overlay._current_theme, "dark")

        self.cfg.set("theme", "light")
        overlay.reload_config()
        self.assertEqual(overlay._current_theme, "light")

if __name__ == "__main__":
    unittest.main()
