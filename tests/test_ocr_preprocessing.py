import os
import sys
import io
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat

# Force offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.dpi import enable_hidpi_awareness
enable_hidpi_awareness()

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPixmap, QColor
from src.capture.ocr_engine import (
    preprocess_for_ocr, compute_otsu_threshold, OCREngine, normalize_ocr_text
)


class TestOCRPreprocessing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def _create_dark_mode_lowres_image(self, text: str = "const port = 8080;") -> Image.Image:
        """Helper to create a low-resolution dark-theme mock image (light text on dark background)."""
        # Low resolution (e.g. 240x50 px) with dark charcoal background #1E1F22 (luminance ~32)
        img = Image.new("RGBA", (260, 50), (30, 31, 34, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("consola.ttf", 16)
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except Exception:
                font = ImageFont.load_default()
        
        # Off-white / light-gray syntax highlighted text
        draw.text((15, 16), text, font=font, fill=(220, 220, 220, 255))
        return img

    def test_dark_mode_inversion_and_upscaling(self):
        """
        Verify that a low-res dark-mode image is upscaled and inverted to black text on white.
        """
        target_text = "const port = 8080;"
        dark_img = self._create_dark_mode_lowres_image(target_text)
        
        # Original properties
        orig_w, orig_h = dark_img.size
        orig_mean_lum = ImageStat.Stat(dark_img.convert("L")).mean[0]
        self.assertLess(orig_mean_lum, 128.0) # Dark theme

        # Apply preprocessing pipeline
        processed = preprocess_for_ocr(dark_img)
        
        # 1. Verify adaptive upscaling took effect
        self.assertGreater(processed.width, orig_w)
        self.assertGreater(processed.height, orig_h)
        self.assertGreaterEqual(processed.width, orig_w * 2)

        # 2. Verify polarity inversion (background is now predominantly white/light)
        gray_processed = processed.convert("L")
        proc_mean_lum = ImageStat.Stat(gray_processed).mean[0]
        self.assertGreater(proc_mean_lum, 128.0) # Light background

        # 3. Verify binarization (high-contrast pixels are primarily 0 or 255)
        hist = gray_processed.histogram()
        bin_extremes_count = hist[0] + hist[255]
        total_pixels = processed.width * processed.height
        # At least 95% of pixels should be cleanly binarized to 0 or 255
        self.assertGreater(bin_extremes_count / total_pixels, 0.95)

    def test_otsu_threshold_computation(self):
        """Test Otsu threshold computation logic."""
        # Create bimodal image (half 40, half 220)
        img = Image.new("L", (100, 100), 40)
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 0, 100, 100], fill=220)
        
        thresh = compute_otsu_threshold(img)
        self.assertTrue(40 <= thresh < 220)

    def test_preprocess_input_types(self):
        """Test preprocess_for_ocr across QImage, QPixmap, bytes, and PIL.Image."""
        pil_orig = Image.new("RGBA", (100, 40), (255, 255, 255, 255))
        
        # 1. PIL Image
        res1 = preprocess_for_ocr(pil_orig)
        self.assertIsInstance(res1, Image.Image)

        # 2. Bytes
        buf = io.BytesIO()
        pil_orig.save(buf, "PNG")
        res2 = preprocess_for_ocr(buf.getvalue())
        self.assertIsInstance(res2, Image.Image)

        # 3. QImage
        qimg = QImage(100, 40, QImage.Format.Format_RGBA8888)
        qimg.fill(QColor(255, 255, 255))
        res3 = preprocess_for_ocr(qimg)
        self.assertIsInstance(res3, Image.Image)

        # 4. QPixmap
        pix = QPixmap(100, 40)
        pix.fill(QColor(255, 255, 255))
        res4 = preprocess_for_ocr(pix)
        self.assertIsInstance(res4, Image.Image)

    def test_dark_mode_end_to_end_recognition(self):
        """Verify that preprocessed dark-mode image is recognized by OCREngine."""
        dark_img = self._create_dark_mode_lowres_image("function testApp()")
        
        # Perform OCR recognition with integrated preprocessing
        recognized = OCREngine.recognize_pil(dark_img, lang="en-US", preprocess=True)
        self.assertIsInstance(recognized, str)
        self.assertTrue(len(recognized) > 0)
        recognized_lower = recognized.lower()
        self.assertTrue("function" in recognized_lower or "test" in recognized_lower or "app" in recognized_lower)


if __name__ == "__main__":
    unittest.main()
