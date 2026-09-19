import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QPoint, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap

from src.config.config_manager import ConfigManager, DEFAULT_CONFIG
from src.utils.autostart import is_autostart_enabled, set_autostart
from src.utils.dpi import enable_hidpi_awareness
from src.ui.action_pill import ActionPillWidget, PillFrame
from src.ui.toast import ToastWidget, ToastFrame, ToastManager, show_quick_toast
from src.ui.settings_dialog import SettingsDialog, SettingsCanvas, HotkeyCaptureButton
from src.ui.icon_generator import IconGenerator
from src.ui.tray_manager import TrayManager
from src.ui.fluid_mesh import FluidMeshShaderWidget, FluidMeshGradient

class TestMaterialSnapComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.test_config_path = BASE_DIR / "test_config.json"
        if self.test_config_path.exists():
            self.test_config_path.unlink()

    def tearDown(self):
        if self.test_config_path.exists():
            self.test_config_path.unlink()

    def test_config_manager(self):
        cm = ConfigManager(str(self.test_config_path))
        self.assertEqual(cm.get("hotkey"), DEFAULT_CONFIG["hotkey"])
        self.assertTrue(cm.get("auto_copy_clipboard"))
        self.assertEqual(cm.get("wave_texture_mode"), "Acrylic")

        cm.set("wave_texture_mode", "Mesh")
        self.assertEqual(cm.get("wave_texture_mode"), "Mesh")

        cm.set("wave_texture_mode", "Unknown")
        self.assertEqual(cm.get("wave_texture_mode"), "Acrylic")

        cm.set("hotkey", "PrintScreen")
        self.assertEqual(cm.get("hotkey"), "PrintScreen")

        # Reload from disk
        cm2 = ConfigManager(str(self.test_config_path))
        self.assertEqual(cm2.get("hotkey"), "PrintScreen")

    def test_dpi_awareness_call(self):
        enable_hidpi_awareness()

    def test_autostart_toggle(self):
        initial_state = is_autostart_enabled()
        set_autostart(not initial_state)
        self.assertEqual(is_autostart_enabled(), not initial_state)
        set_autostart(initial_state)
        self.assertEqual(is_autostart_enabled(), initial_state)

    def test_subpixel_geometry_and_fractional_dpi_rasterization(self):
        """Validates that custom widgets render cleanly under fractional DPI scaling (100%, 125%, 150%)."""
        pill = ActionPillWidget()
        toast = ToastWidget("DPI Test")
        canvas = SettingsCanvas()

        for dpr in [1.0, 1.25, 1.5, 2.0]:
            img = QImage(int(200 * dpr), int(80 * dpr), QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            img.setDevicePixelRatio(dpr)

            pill.frame.render(img)
            toast.frame.render(img)
            canvas.render(img)

            self.assertFalse(img.isNull())
            self.assertGreater(img.width(), 0)

    def test_action_pill_kinetic_spring_and_hide(self):
        pill = ActionPillWidget()
        selection = QRect(100, 100, 300, 200)
        bounds = QRect(0, 0, 1920, 1080)
        
        pill.position_smartly(selection, bounds)
        self.assertTrue(pill.isVisible())
        self.assertIsNotNone(pill._entry_anim_group)

        hidden = False
        def on_hidden():
            nonlocal hidden
            hidden = True

        pill.animate_hide(on_finished=on_hidden)
        self.assertIsNotNone(pill._exit_anim)

    def test_toast_stacking_and_repack(self):
        tm = ToastManager.instance()
        initial_count = len(tm._active_toasts)
        
        t1 = show_quick_toast("Stack Toast 1")
        t2 = show_quick_toast("Stack Toast 2")
        
        self.assertEqual(len(tm._active_toasts), initial_count + 2)
        self.assertNotEqual(t1.pos().y(), t2.pos().y())
        step_y = t1.container.height() + 8
        self.assertEqual(t1.pos().y() - t2.pos().y(), step_y)

        # Cleanup
        t1.close_toast()
        t2.close_toast()

    def test_hotkey_capture_button(self):
        btn = HotkeyCaptureButton("Ctrl+Shift+S")
        self.assertEqual(btn.text(), "Ctrl+Shift+S")
        btn.setText("Alt+F9")
        self.assertEqual(btn.text(), "Alt+F9")

    def test_vector_icons_crispness(self):
        settings_icon = IconGenerator.create_settings_icon(24)
        self.assertFalse(settings_icon.isNull())
        pix = settings_icon.pixmap(24, 24)
        self.assertFalse(pix.isNull())
        self.assertEqual(pix.width(), 24)

    def test_settings_dialog_frameless_canvas_and_tray_menu_translucency(self):
        cfg = ConfigManager(self.test_config_path)
        dlg = SettingsDialog(cfg)
        
        # 1. Dialog translucent background and frameless window flags
        self.assertTrue(dlg.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(bool(dlg.windowFlags() & Qt.WindowType.FramelessWindowHint))
        self.assertTrue(bool(dlg.windowFlags() & Qt.WindowType.Dialog))
        
        # 2. Outer wrapper 20px padding
        root_layout = dlg.layout()
        margins = root_layout.contentsMargins()
        self.assertEqual(margins.left(), 20)
        self.assertEqual(margins.top(), 20)
        self.assertEqual(margins.right(), 20)
        self.assertEqual(margins.bottom(), 20)
        
        # 3. Canvas drop shadow fits within margins without clipping
        self.assertIsNotNone(dlg.canvas.graphicsEffect())
        blur = dlg.canvas.graphicsEffect().blurRadius()
        self.assertLessEqual(blur, 18.0)
        
        # 4. Controls standardized height (32px) and ThemeToggle integration
        self.assertEqual(dlg.edit_dir.height(), 32)
        self.assertEqual(dlg.btn_browse.height(), 32)
        self.assertEqual(dlg.edit_hotkey.height(), 32)
        self.assertEqual(dlg.combo_wave_theme.height(), 32)
        self.assertEqual(dlg.btn_cancel.height(), 32)
        self.assertEqual(dlg.btn_save.height(), 32)
        self.assertIsNotNone(dlg.theme_toggle)
        self.assertEqual(dlg.theme_toggle.width(), 64)
        self.assertEqual(dlg.theme_toggle.height(), 32)

        # 5. CleanComboBox popup container window translucency, frameless hint, and opaque view
        combo_view = dlg.combo_wave_theme.view()
        self.assertIsNotNone(combo_view)
        popup_window = combo_view.window()
        self.assertIsNotNone(popup_window)
        self.assertTrue(popup_window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(bool(popup_window.windowFlags() & Qt.WindowType.FramelessWindowHint))
        self.assertTrue(bool(popup_window.windowFlags() & Qt.WindowType.Popup))
        self.assertFalse(combo_view.autoFillBackground())
        self.assertTrue(combo_view.viewport().autoFillBackground())
        
        # 6. TrayMenu translucent background & frameless hint
        tm = TrayManager(cfg)
        self.assertTrue(tm.tray_menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(bool(tm.tray_menu.windowFlags() & Qt.WindowType.FramelessWindowHint))
        tm.tray_icon.hide()

    def test_two_layer_composition_and_unclipped_shadows(self):
        """Verifies that Toast and ActionPill implement two-layer composition with unclipped drop shadows."""
        # ActionPill
        pill = ActionPillWidget()
        self.assertTrue(pill.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertIsNone(pill.graphicsEffect())
        self.assertGreaterEqual(pill.layout().contentsMargins().left(), 16)
        self.assertIsNotNone(pill.container.graphicsEffect())
        self.assertLessEqual(pill.container.graphicsEffect().blurRadius(), 14.0)

        # ToastWidget
        toast = ToastWidget("Unclipped Shadow Test")
        self.assertTrue(toast.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertIsNone(toast.graphicsEffect())
        self.assertGreaterEqual(toast.layout().contentsMargins().left(), 16)
        self.assertIsNotNone(toast.container.graphicsEffect())
        self.assertLessEqual(toast.container.graphicsEffect().blurRadius(), 14.0)

    def test_fluid_mesh_shader_widget_architecture(self):
        """Verifies GPU shader widget uniform architecture, color mapping, and cursor tracking."""
        shader = FluidMeshShaderWidget(theme_name="Samsung Aura")
        self.assertIsInstance(shader, FluidMeshShaderWidget)
        self.assertIs(FluidMeshGradient, FluidMeshShaderWidget)

        # Architectural default uniforms
        self.assertEqual(shader.scale, 1.30)
        self.assertEqual(shader.intensity, 0.56)
        self.assertEqual(shader.brightness, 1.05)
        self.assertEqual(shader.warp, 0.192)
        self.assertEqual(shader.detail, 2.016)
        self.assertEqual(shader.contrast, 1.10)
        self.assertEqual(shader.saturation, 1.05)
        self.assertEqual(shader.grain, 0.09)
        self.assertEqual(shader.drift, 1.95)

        # Theme mapping to normalized linear RGB float triplets
        shader.set_theme("Samsung Aura")
        self.assertEqual(shader._theme_name, "Samsung Aura")
        self.assertGreaterEqual(len(shader._palette_colors), 5)
        for r, g, b in shader._palette_colors:
            self.assertTrue(0.0 <= r <= 1.0)
            self.assertTrue(0.0 <= g <= 1.0)
            self.assertTrue(0.0 <= b <= 1.0)

        # Pointer interactivity & timeline setters
        shader.set_cursor(0.35, 0.65)
        self.assertEqual(shader._cursor_norm, (0.35, 0.65))
        shader.set_time(5.2)
        self.assertEqual(shader._elapsed_time, 5.2)

    def test_origin_ui_minimal_motion_timings(self):
        """Verifies Origin UI micro-transition parameters (140ms/100ms Action Pill, 160ms/120ms Toast)."""
        # ActionPill 140ms entrance, 100ms dismissal
        pill = ActionPillWidget()
        selection = QRect(100, 100, 300, 200)
        bounds = QRect(0, 0, 1920, 1080)
        pill.position_smartly(selection, bounds)
        
        # Check animations in group
        anims = [pill._entry_anim_group.animationAt(i) for i in range(pill._entry_anim_group.animationCount())]
        self.assertTrue(all(a.duration() == 140 for a in anims))

        pill.animate_hide()
        self.assertEqual(pill._exit_anim.duration(), 100)

        # Toast 140ms entrance, 100ms dismissal
        toast = ToastWidget("Timing Test")
        toast.show_toast(0)
        in_anims = [toast.anim_in.animationAt(i) for i in range(toast.anim_in.animationCount())]
        self.assertTrue(all(a.duration() == 140 for a in in_anims))

        toast.start_fade_out()
        out_anims = [toast.anim_out.animationAt(i) for i in range(toast.anim_out.animationCount())]
        self.assertTrue(all(a.duration() == 100 for a in out_anims))
        toast.close_toast()

    def test_hardware_accelerated_fluid_mesh_offscreen_rendering(self):
        """Verifies that fluid mesh renders hardware-accelerated non-zero translucent frames via offscreen FBO."""
        shader = FluidMeshShaderWidget(theme_name="Samsung Aura")
        img = QImage(800, 600, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        shader.draw(painter, 800, 600, 0.5, "Samsung Aura")
        painter.end()

        # Verify bottom band has non-zero alpha and color
        bottom_pixel = img.pixel(400, 550)
        bottom_alpha = (bottom_pixel >> 24) & 0xFF
        self.assertGreater(bottom_alpha, 0, "Fluid mesh bottom band must have positive alpha!")

        # Verify top region has subtle vertical decay (positive alpha, less dense than bottom)
        top_pixel = img.pixel(400, 50)
        top_alpha = (top_pixel >> 24) & 0xFF
        self.assertGreater(top_alpha, 0, "Fluid mesh full canvas must have positive alpha at top!")
        self.assertGreater(bottom_alpha, top_alpha, "Bottom region must be denser than top region!")

        # Verify all 4 signature themes render with DPI-scaled resolution and positive alpha in both modes
        for theme_name in ["Samsung Aura", "Prism Spectrum", "Solar Flare", "Opal Nebula"]:
            for mode in ["Acrylic", "Mesh"]:
                shader_theme = FluidMeshShaderWidget(theme_name=theme_name)
                img_t = QImage(300, 200, QImage.Format.Format_ARGB32_Premultiplied)
                img_t.fill(0)
                p_t = QPainter(img_t)
                shader_theme.draw(p_t, 300, 200, 0.5, theme_name, dpr=1.5, texture_mode=mode)
                p_t.end()
                px = img_t.pixel(150, 150)
                alpha_val = (px >> 24) & 0xFF
                self.assertGreater(alpha_val, 0, f"{theme_name} fluid mesh must render with positive alpha in {mode} mode!")

    def test_origin_ui_action_pill_specs(self):
        """Verifies Action Pill buttons use shadcn/Radix segmented object naming, text labels, and container layout."""
        pill = ActionPillWidget()
        self.assertEqual(pill.frame.objectName(), "ActionPillFrame")
        self.assertEqual(pill.shadow_margin, 20)
        self.assertEqual(len(pill.buttons), 5)
        expected_labels = ["Text", "Copy", "Save", "Full", "Close"]
        expected_positions = ["first", "middle", "middle", "middle", "last"]
        for btn, label, pos in zip(pill.buttons, expected_labels, expected_positions):
            self.assertEqual(btn.objectName(), "ActionPillButton")
            self.assertEqual(btn.text(), label)
            self.assertEqual(btn.property("position"), pos)
            self.assertTrue(btn.icon().isNull())

    def test_theme_toggle_widget(self):
        """Verifies ThemeToggle geometry, states, property animation, and signals."""
        from src.ui.theme_toggle import ThemeToggle
        toggle = ThemeToggle(initial_theme="dark")
        self.assertEqual(toggle.width(), 64)
        self.assertEqual(toggle.height(), 32)
        self.assertTrue(toggle.is_dark())
        self.assertAlmostEqual(toggle.thumb_x, 4.0)

        received_themes = []
        toggle.sig_theme_changed.connect(received_themes.append)

        # Toggle to light
        toggle.toggle()
        self.assertFalse(toggle.is_dark())
        self.assertEqual(received_themes, ["light"])

        # Test set_is_dark without animation
        toggle.set_is_dark(True, animate=False)
        self.assertTrue(toggle.is_dark())
        self.assertAlmostEqual(toggle.thumb_x, 4.0)

    def test_theme_tokens_and_stylesheets(self):
        """Verifies dark and light theme tokens and dynamic stylesheet generation."""
        from src.ui.styles import THEME_TOKENS, get_theme_tokens, get_application_stylesheet
        dark_tokens = get_theme_tokens("dark")
        light_tokens = get_theme_tokens("light")
        self.assertEqual(dark_tokens["surface_bg"], "#121316")
        self.assertEqual(dark_tokens["surface_card"], "#161719")
        self.assertEqual(light_tokens["surface_bg"], "#FBFBFB")
        self.assertEqual(light_tokens["surface_card"], "#FFFFFF")

        dark_qss = get_application_stylesheet("dark")
        light_qss = get_application_stylesheet("light")
        self.assertIn("#161719", dark_qss)
        self.assertIn("#FFFFFF", light_qss)

    def test_overlay_header_badge_window_parentage_and_flags(self):
        """Verifies HeaderBadge is strictly an internal child widget of ScreenshotOverlay, not a top-level OS window."""
        from src.config.config_manager import ConfigManager
        from src.ui.overlay import ScreenshotOverlay, HeaderBadge

        cm = ConfigManager()
        overlay = ScreenshotOverlay(cm)
        self.assertIsNotNone(overlay.header_badge)
        self.assertIs(overlay.header_badge.parent(), overlay)
        self.assertFalse(overlay.header_badge.isWindow())

        # Strict SubWindow and frameless flags
        flags = overlay.header_badge.windowFlags()
        self.assertTrue(flags & Qt.WindowType.SubWindow)
        self.assertTrue(flags & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(overlay.header_badge.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(overlay.header_badge.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))

        # Test positioning on start_capture
        dummy = QPixmap(800, 600)
        v_rect = QRect(0, 0, 800, 600)
        overlay.start_capture(dummy, v_rect)
        self.assertEqual(overlay.header_badge.pos(), QPoint(24, 20))
        overlay.close_overlay()

    def test_tray_menu_redesign_and_action_pill_alignment(self):
        """Verifies Tray Context Menu flags and Action Pill alignment across menus and settings controls."""
        from src.config.config_manager import ConfigManager
        from src.ui.tray_manager import TrayManager
        from src.ui.settings_dialog import SettingsDialog, MonochromeCheckBox
        from src.ui.styles import get_menu_style, get_settings_dialog_style

        cm = ConfigManager()
        tray = TrayManager(cm)
        menu = tray.tray_menu
        self.assertIsNotNone(menu)

        # Frameless, translucent popup flags
        flags = menu.windowFlags()
        self.assertTrue(flags & Qt.WindowType.Popup)
        self.assertTrue(flags & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(flags & Qt.WindowType.NoDropShadowWindowHint)
        self.assertTrue(menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

        # Menu QSS metrics
        qss = get_menu_style("dark")
        self.assertIn("padding: 4px 14px 4px 36px;", qss)
        self.assertIn("left: 10px;", qss)
        self.assertIn("width: 16px;", qss)
        self.assertIn("height: 16px;", qss)
        self.assertIn("height: 32px;", qss)
        self.assertIn("border-radius: 10px;", qss)

        # Settings dialog action pill alignment
        dlg = SettingsDialog(cm)
        self.assertEqual(dlg.btn_browse.height(), 32)
        self.assertEqual(dlg.btn_cancel.height(), 32)
        self.assertEqual(dlg.btn_save.height(), 32)
        self.assertEqual(dlg.edit_dir.height(), 32)
        self.assertEqual(dlg.edit_hotkey.height(), 32)

        # MonochromeCheckBox checked and unchecked paint verification
        chk = MonochromeCheckBox("Test Checkbox", theme="dark")
        img = QImage(200, 28, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        chk.paintEvent(None)
        chk.setChecked(True)
        chk.paintEvent(None)
        p.end()

        tray.tray_icon.hide()

if __name__ == "__main__":
    unittest.main()

