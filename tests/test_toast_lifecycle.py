import os
import sys
import unittest
from pathlib import Path

# Force offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from src.ui.toast import show_quick_toast, ToastManager, ToastState

class TestToastLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_toast_lifecycle_timing(self):
        toast = show_quick_toast("Test Lifecycle Toast", duration_ms=3000)
        self.assertIsNotNone(toast)

        # 1. At t = 100ms: Must be visible and animating in
        QTest.qWait(100)
        self.assertTrue(toast.isVisible())
        self.assertTrue(toast.windowOpacity() > 0.0)

        # 2. At t = 1500ms: Must be fully visible and in VISIBLE state (did NOT disappear)
        QTest.qWait(1400) # Cumulative t = 1500ms
        self.assertTrue(toast.isVisible())
        self.assertEqual(toast._state, ToastState.VISIBLE)
        self.assertEqual(toast.windowOpacity(), 1.0)

        # 3. At t = 3800ms: Must have cleanly completed fade-out and closed
        QTest.qWait(2300) # Cumulative t = 3800ms
        self.assertEqual(toast._state, ToastState.CLOSED)
        self.assertFalse(toast.isVisible())
        self.assertNotIn(toast, ToastManager.instance()._active_toasts)

if __name__ == "__main__":
    unittest.main()
