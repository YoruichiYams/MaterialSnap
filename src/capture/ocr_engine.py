import io
import re
import sys
import gc
import asyncio
from typing import Optional, List, Union
from PIL import Image, ImageOps, ImageStat, ImageFilter

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtGui import QImage, QPixmap

# Try importing Windows Native OCR (WinRT / winocr)
_HAS_WINRT_OCR = False
try:
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.storage.streams import DataWriter
    from winrt.windows.graphics.imaging import SoftwareBitmap, BitmapPixelFormat
    _HAS_WINRT_OCR = True
except Exception:
    _HAS_WINRT_OCR = False

# Try importing pytesseract
_HAS_PYTESSERACT = False
try:
    import pytesseract
    _HAS_PYTESSERACT = True
except Exception:
    _HAS_PYTESSERACT = False


def qimage_to_pil(qimage: QImage) -> Image.Image:
    """
    Converts a QImage directly into a PIL Image in-memory with zero disk I/O.
    Ensures RGBA format and frees intermediate memory immediately.
    """
    if qimage.isNull() or qimage.width() == 0 or qimage.height() == 0:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    # Convert to RGBA8888 for standard memory alignment
    if qimage.format() != QImage.Format.Format_RGBA8888:
        formatted = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
    else:
        formatted = qimage

    width = formatted.width()
    height = formatted.height()
    
    # Read raw bytes directly from QImage memory buffer
    raw_bytes = bytes(formatted.constBits())
    pil_img = Image.frombytes("RGBA", (width, height), raw_bytes)
    return pil_img


def compute_otsu_threshold(img: Image.Image) -> int:
    """
    Computes Otsu's optimal global binarization threshold from 256-bin histogram
    in pure Python without OpenCV or heavy external dependencies.
    """
    hist = img.histogram()
    total = sum(hist)
    if total == 0:
        return 128
    sum_total = sum(i * hist[i] for i in range(256))
    sum_b = 0
    w_b = 0
    max_variance = 0.0
    threshold = 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        variance = w_b * w_f * ((m_b - m_f) ** 2)
        if variance > max_variance:
            max_variance = variance
            threshold = t
    return threshold


def preprocess_for_ocr(image: Union[QImage, QPixmap, Image.Image, bytes]) -> Image.Image:
    """
    High-precision, lightweight OCR preprocessing pipeline using Pillow (PIL).
    Maximizes recognition accuracy for code editors, browser text, and dark-mode themes.

    Pipeline Steps:
    1. Input conversion (QImage / QPixmap / bytes / PIL.Image)
    2. Grayscale conversion ('L')
    3. Adaptive upscaling (2x - 2.5x BICUBIC for <600px dimensions)
    4. Polarity detection & inversion (dark theme -> black on white)
    5. Monochrome contrast (autocontrast) & Otsu threshold binarization
    6. Output format conversion to RGBA for engine compatibility
    """
    if isinstance(image, QImage):
        pil_img = qimage_to_pil(image)
    elif isinstance(image, QPixmap):
        pil_img = qimage_to_pil(image.toImage())
    elif isinstance(image, bytes):
        pil_img = Image.open(io.BytesIO(image))
    elif isinstance(image, Image.Image):
        pil_img = image
    else:
        raise TypeError(f"Unsupported image type for OCR preprocessing: {type(image)}")

    if pil_img.width == 0 or pil_img.height == 0:
        return Image.new("RGBA", (1, 1), (255, 255, 255, 255))

    # 1. Grayscale conversion (Luminance)
    gray = pil_img.convert("L")
    w, h = gray.size

    # 2. Adaptive Upscaling to bring characters to optimal 30-40px height
    if w < 600 or h < 600:
        if w < 300 or h < 150:
            scale = 2.5
        else:
            scale = 2.0
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        gray = gray.resize((new_w, new_h), Image.Resampling.BICUBIC)

    # 3. Polarity Detection & Inversion
    stat = ImageStat.Stat(gray)
    mean_lum = stat.mean[0] if stat.mean else 128.0
    if mean_lum < 128.0:
        gray = ImageOps.invert(gray)

    # 4. Monochrome Contrast & Thresholding
    gray = ImageOps.autocontrast(gray, cutoff=1)
    thresh = compute_otsu_threshold(gray)
    binary = gray.point(lambda p: 255 if p > thresh else 0)

    # 5. Output as RGBA for maximum engine compatibility
    return binary.convert("RGBA")


def normalize_ocr_text(text: str) -> str:
    """
    Normalizes extracted OCR text by trimming excessive blank lines,
    normalizing Unix/Windows line endings (\n), and stripping whitespace.
    """
    if not text:
        return ""
    
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Split into lines and strip whitespace on each line
    lines = [line.strip() for line in text.splitlines()]
    
    # Remove leading and trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    # Collapse sequences of consecutive blank lines into a single blank line
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned_lines.append("")
                prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False

    return "\n".join(cleaned_lines).strip()


class OCREngine:
    """
    Offline Optical Character Recognition Engine.
    Primary: Windows Native OCR (winrt.windows.media.ocr) - zero install, offline, native Windows 10/11.
    Fallback: pytesseract - graceful error handling if Tesseract is missing.
    """

    @classmethod
    def is_available(cls) -> bool:
        """Returns True if at least one OCR backend is available."""
        return _HAS_WINRT_OCR or _HAS_PYTESSERACT

    @classmethod
    def get_available_languages(cls) -> List[str]:
        """Returns list of installed Windows OCR language tags."""
        if _HAS_WINRT_OCR:
            try:
                return [l.language_tag for l in OcrEngine.available_recognizer_languages]
            except Exception:
                pass
        return []

    @classmethod
    def recognize_pil(cls, pil_img: Image.Image, lang: Optional[str] = None, preprocess: bool = True) -> str:
        """
        Recognizes text from a PIL Image in-memory using the best available backend.
        Optionally runs high-precision preprocessing pipeline.
        """
        if pil_img.width < 2 or pil_img.height < 2:
            return ""

        # Run preprocessing pipeline
        if preprocess:
            processed_img = preprocess_for_ocr(pil_img)
        else:
            processed_img = pil_img.convert("RGBA") if pil_img.mode != "RGBA" else pil_img

        # 1. Primary Engine: Windows Native OCR
        if _HAS_WINRT_OCR:
            try:
                text = cls._recognize_winrt(processed_img, lang)
                if text.strip():
                    return normalize_ocr_text(text)
            except Exception as e:
                print(f"[OCREngine] Windows Native OCR failed: {e}")

        # 2. Fallback Engine: pytesseract
        if _HAS_PYTESSERACT:
            try:
                text = pytesseract.image_to_string(processed_img, lang=lang or "eng")
                if text.strip():
                    return normalize_ocr_text(text)
            except Exception as e:
                print(f"[OCREngine] pytesseract fallback failed: {e}")

        return ""

    @classmethod
    def _recognize_winrt(cls, pil_img: Image.Image, lang: Optional[str] = None) -> str:
        """
        Performs Windows Native OCR on the given PIL Image using WinRT API.
        Attempts user profile languages, en-US, and installed languages if first attempt returns empty.
        """
        raw_bytes = pil_img.tobytes()
        writer = DataWriter()
        writer.write_bytes(raw_bytes)
        img_buffer = writer.detach_buffer()

        async def _run_recognition():
            # Build list of candidate languages to test
            available = list(OcrEngine.available_recognizer_languages)
            candidate_languages = []

            if lang:
                try:
                    candidate_languages.append(Language(lang))
                except Exception:
                    pass

            # Try user profile language first
            try:
                up_engine = OcrEngine.try_create_from_user_profile_languages()
                if up_engine and up_engine.recognizer_language:
                    candidate_languages.append(up_engine.recognizer_language)
            except Exception:
                pass

            # Try en-US
            try:
                candidate_languages.append(Language("en-US"))
            except Exception:
                pass

            # Append all remaining installed languages
            for avail_lang in available:
                if not any(avail_lang.language_tag.lower() == cl.language_tag.lower() for cl in candidate_languages):
                    candidate_languages.append(avail_lang)

            for cand_lang in candidate_languages:
                try:
                    if not OcrEngine.is_language_supported(cand_lang):
                        continue
                    engine = OcrEngine.try_create_from_language(cand_lang)
                    if not engine:
                        continue

                    sb = SoftwareBitmap.create_copy_from_buffer(
                        img_buffer, BitmapPixelFormat.RGBA8, pil_img.width, pil_img.height
                    )
                    res = await engine.recognize_async(sb)
                    
                    if res and res.lines:
                        line_texts = [line.text for line in res.lines if line.text]
                        combined = "\n".join(line_texts)
                        if combined.strip():
                            return combined
                    elif res and res.text and res.text.strip():
                        return res.text
                except Exception:
                    continue

            return ""

        return asyncio.run(_run_recognition())

    @classmethod
    def recognize_qimage(cls, qimage: QImage, lang: Optional[str] = None, preprocess: bool = True) -> str:
        """
        Recognizes text from a QImage with automatic memory cleanup.
        """
        if qimage.isNull() or qimage.width() == 0 or qimage.height() == 0:
            return ""

        pil_img = qimage_to_pil(qimage)
        try:
            return cls.recognize_pil(pil_img, lang=lang, preprocess=preprocess)
        finally:
            del pil_img
            gc.collect()

    @classmethod
    def recognize_qpixmap(cls, qpixmap: QPixmap, lang: Optional[str] = None, preprocess: bool = True) -> str:
        """
        Recognizes text from a QPixmap.
        """
        if qpixmap.isNull():
            return ""
        qimage = qpixmap.toImage()
        return cls.recognize_qimage(qimage, lang=lang, preprocess=preprocess)


class OCRSignals(QObject):
    """Signals for asynchronous OCR worker."""
    sig_finished = Signal(str)
    sig_error = Signal(str)


class OCRWorker(QThread):
    """
    Lightweight QThread worker executing OCR recognition asynchronously
    without freezing the main UI.
    """
    sig_finished = Signal(str)
    sig_error = Signal(str)

    def __init__(self, image: QImage, lang: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.image = image
        self.lang = lang
        self.finished.connect(self.deleteLater)

    @property
    def signals(self):
        """Compatibility property exposing sig_finished and sig_error."""
        return self

    def run(self):
        try:
            recognized_text = OCREngine.recognize_qimage(self.image, lang=self.lang)
            self.sig_finished.emit(recognized_text)
        except Exception as err:
            self.sig_error.emit(str(err))
        finally:
            self.image = QImage()
            gc.collect()
