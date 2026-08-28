import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config.config_manager import ConfigManager, DEFAULT_CONFIG
from src.utils.autostart import is_autostart_enabled, set_autostart
from src.utils.dpi import enable_hidpi_awareness

class TestMaterialSnapComponents(unittest.TestCase):

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

        cm.set("hotkey", "PrintScreen")
        self.assertEqual(cm.get("hotkey"), "PrintScreen")

        # Reload from disk
        cm2 = ConfigManager(str(self.test_config_path))
        self.assertEqual(cm2.get("hotkey"), "PrintScreen")

    def test_dpi_awareness_call(self):
        # Should execute safely without throwing exceptions
        enable_hidpi_awareness()

    def test_autostart_toggle(self):
        initial_state = is_autostart_enabled()
        # Toggle test
        set_autostart(not initial_state)
        self.assertEqual(is_autostart_enabled(), not initial_state)
        # Restore initial state
        set_autostart(initial_state)
        self.assertEqual(is_autostart_enabled(), initial_state)

if __name__ == "__main__":
    unittest.main()
