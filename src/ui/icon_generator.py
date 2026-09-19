from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
from PySide6.QtCore import Qt, QRectF, QPointF

class IconGenerator:
    """
    Dynamically generates modern vector icons for high-DPI displays with strict neutral monochrome styling.
    Generates multi-DPI pixmaps (1x and 2x Retina backing stores) to eliminate fractional DPI blur.
    """

    @staticmethod
    def _create_multi_dpi_icon(size: int, render_fn) -> QIcon:
        """Helper to create a QIcon containing 1.0x, 1.25x, 1.5x, and 2.0x HiDPI pixmap representations."""
        icon = QIcon()
        for scale in [1.0, 1.25, 1.5, 2.0]:
            px_size = int(round(size * scale))
            pix = QPixmap(px_size, px_size)
            pix.fill(Qt.transparent)
            pix.setDevicePixelRatio(scale)
            
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            
            render_fn(painter, size)
            painter.end()
            
            icon.addPixmap(pix)
        return icon

    @classmethod
    def create_app_icon(cls, size: int = 64) -> QIcon:
        def render(painter: QPainter, s: int):
            rect = QRectF(2, 2, s - 4, s - 4)

            # Rounded squircle background with neutral dark surface
            path = QPainterPath()
            path.addRoundedRect(rect, s * 0.28, s * 0.28)

            bg_grad = QLinearGradient(0, 0, s, s)
            bg_grad.setColorAt(0.0, QColor("#1E1F22"))
            bg_grad.setColorAt(1.0, QColor("#161719"))
            painter.fillPath(path, bg_grad)

            # Crisp Monochromatic Border
            border_pen = QPen(QColor(255, 255, 255, 45), max(1.0, s * 0.035))
            painter.setPen(border_pen)
            painter.drawPath(path)

            # Draw Lens / Aperture & Monochromatic neutral dots
            c = s / 2.0
            r = s * 0.24

            # Lens ring
            lens_pen = QPen(QColor("#FFFFFF"), max(1.5, s * 0.05))
            painter.setPen(lens_pen)
            painter.drawEllipse(QPointF(c, c), r, r)

            # Monochromatic dynamic dots inside (White, Platinum, Silver, Soft Gray)
            dot_r = s * 0.055
            offset = r * 0.45
            colors = [
                (QColor("#FFFFFF"), c - offset, c - offset), # Pure White
                (QColor("#E8EAED"), c + offset, c - offset), # Platinum White
                (QColor("#BDC1C6"), c - offset, c + offset), # Silver
                (QColor("#9AA0A6"), c + offset, c + offset), # Soft Gray
            ]

            painter.setPen(Qt.NoPen)
            for col, dx, dy in colors:
                painter.setBrush(QBrush(col))
                painter.drawEllipse(QPointF(dx, dy), dot_r, dot_r)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_copy_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        """Dual layered sheets: solid front sheet with folded dog-ear notch masking background outline sheet."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            # 1. Background sheet outline (upper-left)
            back = QPainterPath()
            back.moveTo(s * 0.22, s * 0.54)
            back.lineTo(s * 0.22, s * 0.22)
            back.lineTo(s * 0.54, s * 0.22)
            painter.drawPath(back)

            # 2. Solid front sheet (lower-right) with folded top-right notch
            fx1, fy1 = s * 0.34, s * 0.34
            fx2, fy2 = s * 0.78, s * 0.78
            notch = s * 0.14

            front = QPainterPath()
            front.moveTo(fx1, fy1)
            front.lineTo(fx2 - notch, fy1)
            front.lineTo(fx2, fy1 + notch)
            front.lineTo(fx2, fy2)
            front.lineTo(fx1, fy2)
            front.closeSubpath()

            painter.fillPath(front, QBrush(QColor("#1E1F22")))
            painter.drawPath(front)

            # Fold notch flap
            fold = QPainterPath()
            fold.moveTo(fx2 - notch, fy1)
            fold.lineTo(fx2 - notch, fy1 + notch)
            fold.lineTo(fx2, fy1 + notch)
            painter.drawPath(fold)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_save_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        """Retro 3.5\" floppy disk silhouette with shutter and label cutouts."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            x1, y1 = s * 0.20, s * 0.20
            x2, y2 = s * 0.80, s * 0.80
            bevel = s * 0.12

            # Outer silhouette with top-right beveled notch
            disk = QPainterPath()
            disk.moveTo(x1, y1)
            disk.lineTo(x2 - bevel, y1)
            disk.lineTo(x2, y1 + bevel)
            disk.lineTo(x2, y2)
            disk.lineTo(x1, y2)
            disk.closeSubpath()
            painter.drawPath(disk)

            # Top sliding metal shutter cutout
            shutter = QPainterPath()
            shutter.addRect(QRectF(s * 0.35, y1, s * 0.30, s * 0.22))
            painter.drawPath(shutter)

            # Bottom paper label cutout
            label_rect = QPainterPath()
            label_rect.addRoundedRect(QRectF(s * 0.30, s * 0.52, s * 0.40, s * 0.22), 1.5, 1.5)
            painter.drawPath(label_rect)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_close_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        """Thick geometric diagonal cross ('X')."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 2.8, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
            painter.setPen(pen)
            painter.drawLine(QPointF(s * 0.28, s * 0.28), QPointF(s * 0.72, s * 0.72))
            painter.drawLine(QPointF(s * 0.72, s * 0.28), QPointF(s * 0.28, s * 0.72))

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_fullscreen_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        """Dashed corner brackets with 4 diagonal expansion arrows."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)

            m = s * 0.18
            l = s * 0.16
            # 4 Corner Brackets
            painter.drawLine(QPointF(m, m + l), QPointF(m, m))
            painter.drawLine(QPointF(m, m), QPointF(m + l, m))

            painter.drawLine(QPointF(s - m - l, m), QPointF(s - m, m))
            painter.drawLine(QPointF(s - m, m), QPointF(s - m, m + l))

            painter.drawLine(QPointF(m, s - m - l), QPointF(m, s - m))
            painter.drawLine(QPointF(m, s - m), QPointF(m + l, s - m))

            painter.drawLine(QPointF(s - m - l, s - m), QPointF(s - m, s - m))
            painter.drawLine(QPointF(s - m, s - m), QPointF(s - m, s - m - l))

            # 4 Diagonal Expansion Arrows
            c = s / 2.0
            d_in = s * 0.08
            d_out = s * 0.22
            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                p1 = QPointF(c + dx * d_in, c + dy * d_in)
                p2 = QPointF(c + dx * d_out, c + dy * d_out)
                painter.drawLine(p1, p2)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_check_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)

            path = QPainterPath()
            path.moveTo(s * 0.22, s * 0.52)
            path.lineTo(s * 0.42, s * 0.72)
            path.lineTo(s * 0.78, s * 0.3)
            painter.drawPath(path)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_folder_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            path = QPainterPath()
            path.moveTo(s * 0.18, s * 0.3)
            path.lineTo(s * 0.4, s * 0.3)
            path.lineTo(s * 0.5, s * 0.4)
            path.lineTo(s * 0.82, s * 0.4)
            path.lineTo(s * 0.82, s * 0.75)
            path.lineTo(s * 0.18, s * 0.75)
            path.closeSubpath()
            painter.drawPath(path)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_ocr_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        """Typographic serif ligature 'Aa'."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)

            # Capital Serif 'A' (Left)
            painter.drawLine(QPointF(s * 0.32, s * 0.24), QPointF(s * 0.18, s * 0.76))
            painter.drawLine(QPointF(s * 0.32, s * 0.24), QPointF(s * 0.46, s * 0.76))
            painter.drawLine(QPointF(s * 0.24, s * 0.58), QPointF(s * 0.40, s * 0.58))
            # Left Leg Serif Foot
            painter.drawLine(QPointF(s * 0.14, s * 0.76), QPointF(s * 0.22, s * 0.76))
            # Right Leg Serif Foot
            painter.drawLine(QPointF(s * 0.42, s * 0.76), QPointF(s * 0.50, s * 0.76))

            # Lowercase Serif 'a' (Right)
            # Stem on right with bottom hook
            painter.drawLine(QPointF(s * 0.74, s * 0.42), QPointF(s * 0.74, s * 0.72))
            painter.drawLine(QPointF(s * 0.74, s * 0.72), QPointF(s * 0.79, s * 0.76))
            # Rounded bowl
            bowl = QPainterPath()
            bowl.addEllipse(QRectF(s * 0.52, s * 0.46, s * 0.22, s * 0.28))
            painter.drawPath(bowl)
            # Top hood/arch
            painter.drawLine(QPointF(s * 0.54, s * 0.44), QPointF(s * 0.74, s * 0.42))

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_settings_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            # Minimalist Sliders/Controls Settings Glyph
            c = s / 2.0
            # Track 1
            painter.drawLine(QPointF(s * 0.22, s * 0.32), QPointF(s * 0.78, s * 0.32))
            painter.setBrush(QBrush(QColor(color)))
            painter.drawEllipse(QPointF(s * 0.40, s * 0.32), s * 0.10, s * 0.10)

            # Track 2
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(QPointF(s * 0.22, s * 0.68), QPointF(s * 0.78, s * 0.68))
            painter.setBrush(QBrush(QColor(color)))
            painter.drawEllipse(QPointF(s * 0.60, s * 0.68), s * 0.10, s * 0.10)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_status_info_icon(cls, size: int = 16, color: str = "#3B82F6") -> QIcon:
        """16x16 circular ring + centered dot/stem 'i' in electric blue (#3B82F6)."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), max(1.0, 1.6 * (s / 16.0)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            c = s / 2.0
            r = s * 0.40
            painter.drawEllipse(QPointF(c, c), r, r)

            # Dot and stem 'i'
            painter.drawLine(QPointF(c, c - s * 0.17), QPointF(c, c - s * 0.17))
            painter.drawLine(QPointF(c, c - s * 0.02), QPointF(c, c + s * 0.20))

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_status_success_icon(cls, size: int = 16, color: str = "#10B981") -> QIcon:
        """16x16 circular ring + centered checkmark in emerald green (#10B981)."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), max(1.0, 1.6 * (s / 16.0)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            c = s / 2.0
            r = s * 0.40
            painter.drawEllipse(QPointF(c, c), r, r)

            # Centered checkmark
            path = QPainterPath()
            path.moveTo(s * 0.31, s * 0.50)
            path.lineTo(s * 0.44, s * 0.65)
            path.lineTo(s * 0.69, s * 0.35)
            painter.drawPath(path)

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_status_warning_icon(cls, size: int = 16, color: str = "#F59E0B") -> QIcon:
        """16x16 rounded triangle + exclamation mark in amber gold (#F59E0B)."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), max(1.0, 1.6 * (s / 16.0)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            c = s / 2.0
            tri = QPainterPath()
            tri.moveTo(c, s * 0.16)
            tri.lineTo(s * 0.85, s * 0.82)
            tri.lineTo(s * 0.15, s * 0.82)
            tri.closeSubpath()
            painter.drawPath(tri)

            # Exclamation mark
            painter.drawLine(QPointF(c, s * 0.38), QPointF(c, s * 0.58))
            painter.drawLine(QPointF(c, s * 0.71), QPointF(c, s * 0.71))

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_status_error_icon(cls, size: int = 16, color: str = "#EF4444") -> QIcon:
        """16x16 circular ring + diagonal cross in coral red (#EF4444)."""
        def render(painter: QPainter, s: int):
            pen = QPen(QColor(color), max(1.0, 1.6 * (s / 16.0)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            c = s / 2.0
            r = s * 0.40
            painter.drawEllipse(QPointF(c, c), r, r)

            # Diagonal cross
            d = s * 0.16
            painter.drawLine(QPointF(c - d, c - d), QPointF(c + d, c + d))
            painter.drawLine(QPointF(c + d, c - d), QPointF(c - d, c + d))

        return cls._create_multi_dpi_icon(size, render)

    @classmethod
    def create_status_icon(cls, variant: str = "info", size: int = 16) -> QIcon:
        v = (variant or "info").lower()
        if v in ("success", "check", "copy", "ocr", "text"):
            return cls.create_status_success_icon(size)
        elif v == "warning":
            return cls.create_status_warning_icon(size)
        elif v in ("error", "fail", "failed"):
            return cls.create_status_error_icon(size)
        else: # "info", "app", "folder", default
            return cls.create_status_info_icon(size)
