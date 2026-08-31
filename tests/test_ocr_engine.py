import os
import sys
import time
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Force offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.dpi import enable_hidpi_awareness
enable_hidpi_awareness()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool, QEventLoop, QTimer
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QFont
from src.capture.ocr_engine import (
    OCREngine, OCRWorker, OCRSignals, qimage_to_pil, normalize_ocr_text
)


class TestOCREngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def _create_synthetic_text_image(self, text: str = "MaterialSnap OCR 2026") -> Image.Image:
        """Helper to create a clean, high-contrast PIL image with rendered text."""
        img = Image.new("RGBA", (500, 150), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        draw.text((30, 50), text, font=font, fill=(0, 0, 0, 255))
        return img

    def test_ocr_engine_availability(self):
        """Verify that at least one OCR backend (Windows Native OCR / winocr) is available."""
        self.assertTrue(OCREngine.is_available())
        langs = OCREngine.get_available_languages()
        self.assertIsInstance(langs, list)
        self.assertTrue(len(langs) > 0)

    def test_synthetic_image_recognition(self):
        """Test OCR recognition on a clean high-contrast synthetic image."""
        target_text = "MaterialSnap OCR 2026"
        pil_img = self._create_synthetic_text_image(target_text)
        
        result = OCREngine.recognize_pil(pil_img, lang="en-US")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        # Check that core text tokens are present (case-insensitive)
        result_lower = result.lower()
        self.assertTrue("material" in result_lower or "snap" in result_lower or "2026" in result_lower)

    def test_empty_and_blank_image(self):
        """Test that empty or tiny blank images return empty string without errors."""
        # 1. Tiny image
        tiny_img = Image.new("RGBA", (2, 2), (255, 255, 255, 255))
        self.assertEqual(OCREngine.recognize_pil(tiny_img), "")

        # 2. Blank white image
        blank_img = Image.new("RGBA", (300, 100), (255, 255, 255, 255))
        result = OCREngine.recognize_pil(blank_img)
        self.assertEqual(result.strip(), "")

        # 3. Null QImage
        null_qimg = QImage()
        self.assertEqual(OCREngine.recognize_qimage(null_qimg), "")

        # 4. Null QPixmap
        null_pix = QPixmap()
        self.assertEqual(OCREngine.recognize_qpixmap(null_pix), "")

    def test_qimage_to_pil_conversion_formats(self):
        """Test in-memory conversion from various QImage formats to PIL Image."""
        # RGBA8888
        qimg1 = QImage(100, 50, QImage.Format.Format_RGBA8888)
        qimg1.fill(QColor(255, 0, 0, 255))
        pil1 = qimage_to_pil(qimg1)
        self.assertEqual(pil1.size, (100, 50))
        self.assertEqual(pil1.mode, "RGBA")
        self.assertEqual(pil1.getpixel((10, 10)), (255, 0, 0, 255))

        # ARGB32
        qimg2 = QImage(80, 40, QImage.Format.Format_ARGB32)
        qimg2.fill(QColor(0, 255, 0, 255))
        pil2 = qimage_to_pil(qimg2)
        self.assertEqual(pil2.size, (80, 40))
        self.assertEqual(pil2.mode, "RGBA")

        # RGB32
        qimg3 = QImage(60, 30, QImage.Format.Format_RGB32)
        qimg3.fill(QColor(0, 0, 255, 255))
        pil3 = qimage_to_pil(qimg3)
        self.assertEqual(pil3.size, (60, 30))
        self.assertEqual(pil3.mode, "RGBA")

    def test_whitespace_normalization(self):
        """Test whitespace normalization helper."""
        self.assertEqual(normalize_ocr_text(""), "")
        self.assertEqual(normalize_ocr_text("   \n\n   \n   "), "")
        
        raw_text = "  Line 1   \n\n\n\n  Line 2   \n  \n"
        normalized = normalize_ocr_text(raw_text)
        self.assertEqual(normalized, "Line 1\n\nLine 2")

    def test_async_ocr_worker_execution(self):
        """Test that OCRWorker executes asynchronously on QThreadPool and emits signals."""
        pil_img = self._create_synthetic_text_image("Async Worker Test")
        
        # Convert to QImage
        qimg = QImage(pil_img.tobytes(), pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
        
        worker = OCRWorker(qimg, lang="en-US")
        
        received_text = None
        error_msg = None
        loop = QEventLoop()

        def on_finished(text):
            nonlocal received_text
            received_text = text
            loop.quit()

        def on_error(err):
            nonlocal error_msg
            error_msg = err
            loop.quit()

        worker.sig_finished.connect(on_finished)
        worker.sig_error.connect(on_error)

        worker.start()

        # Timeout after 5 seconds
        QTimer.singleShot(5000, loop.quit)
        loop.exec()

        self.assertIsNone(error_msg)
        self.assertIsNotNone(received_text)
        self.assertTrue(isinstance(received_text, str))


if __name__ == "__main__":
    unittest.main()
