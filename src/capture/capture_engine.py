from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QRect, QPoint, QSize, Qt
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QImage, QClipboard
from PySide6.QtWidgets import QApplication

class CaptureResult:
    """Represents a captured screenshot or cropped region."""
    def __init__(self, pixmap: QPixmap, capture_rect: QRect, virtual_origin: QPoint):
        self.pixmap = pixmap
        self.capture_rect = capture_rect
        self.virtual_origin = virtual_origin

    def copy_to_clipboard(self) -> bool:
        """Copies the image to the system clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.pixmap)
        return True

    def save(self, filepath: str, format_name: str = "PNG") -> bool:
        """Saves the pixmap to a file path."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            return self.pixmap.save(str(path), format_name)
        except Exception as e:
            print(f"[CaptureResult] Error saving file: {e}")
            return False

class CaptureEngine:
    """Handles multi-monitor screen capturing with HiDPI accuracy."""

    @staticmethod
    def get_virtual_desktop_rect() -> QRect:
        """Calculates the full bounding rectangle covering all connected monitors."""
        screens = QGuiApplication.screens()
        if not screens:
            primary = QGuiApplication.primaryScreen()
            if primary:
                return primary.geometry()
            return QRect(0, 0, 1920, 1080)

        left = min(s.geometry().left() for s in screens)
        top = min(s.geometry().top() for s in screens)
        right = max(s.geometry().right() for s in screens)
        bottom = max(s.geometry().bottom() for s in screens)

        return QRect(left, top, right - left + 1, bottom - top + 1)

    @staticmethod
    def capture_all_screens() -> tuple[QPixmap, QRect]:
        """
        Captures all connected monitors and composes them into a single high-res virtual desktop pixmap.
        Handles negative offsets and fractional DPI per screen.
        Returns (composite_pixmap, virtual_bounding_rect).
        """
        screens = QGuiApplication.screens()
        if not screens:
            primary = QGuiApplication.primaryScreen()
            pix = primary.grabWindow(0) if primary else QPixmap()
            return pix, QRect(0, 0, pix.width(), pix.height())

        v_rect = CaptureEngine.get_virtual_desktop_rect()
        
        # Create full composite canvas
        composite = QPixmap(v_rect.size())
        composite.fill(Qt.black)

        painter = QPainter(composite)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        for screen in screens:
            s_geom = screen.geometry()
            # Grab window at screen coordinates
            screen_pix = screen.grabWindow(0)
            
            # Offset relative to the top-left of the virtual desktop (which can be negative)
            draw_x = s_geom.left() - v_rect.left()
            draw_y = s_geom.top() - v_rect.top()
            target_rect = QRect(draw_x, draw_y, s_geom.width(), s_geom.height())
            
            # Paint scaled to logical rectangle
            painter.drawPixmap(target_rect, screen_pix)

        painter.end()
        return composite, v_rect

    @staticmethod
    def generate_filename(save_dir: str, prefix: str = "Screenshot", ext: str = "png") -> str:
        """Generates a timestamped filepath for saving with path sanitization."""
        from ..utils.path_security import sanitize_filename, validate_save_directory
        safe_dir = validate_save_directory(save_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_prefix = sanitize_filename(prefix, fallback="Screenshot")
        safe_ext = sanitize_filename(ext, fallback="png").lstrip(".")
        filename = f"{safe_prefix}_{timestamp}.{safe_ext.lower()}"
        return str(safe_dir / filename)
