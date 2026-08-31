from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
from PySide6.QtCore import Qt, QRectF, QPointF

class IconGenerator:
    """Dynamically generates modern vector icons for high-DPI displays with strict neutral monochrome styling."""

    @staticmethod
    def create_app_icon(size: int = 64) -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = QRectF(2, 2, size - 4, size - 4)

        # Rounded squircle background with neutral dark surface
        path = QPainterPath()
        path.addRoundedRect(rect, size * 0.28, size * 0.28)

        bg_grad = QLinearGradient(0, 0, size, size)
        bg_grad.setColorAt(0.0, QColor("#1E1F22"))
        bg_grad.setColorAt(1.0, QColor("#161719"))
        painter.fillPath(path, bg_grad)

        # Crisp Monochromatic Border
        border_pen = QPen(QColor(255, 255, 255, 45), size * 0.035)
        painter.setPen(border_pen)
        painter.drawPath(path)

        # Draw Lens / Aperture & Monochromatic neutral dots
        c = size / 2
        r = size * 0.24

        # Lens ring
        lens_pen = QPen(QColor("#FFFFFF"), size * 0.05)
        painter.setPen(lens_pen)
        painter.drawEllipse(QPointF(c, c), r, r)

        # Monochromatic dynamic dots inside (White, Platinum, Silver, Soft Gray)
        dot_r = size * 0.055
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

        painter.end()
        return QIcon(pix)

    @staticmethod
    def create_copy_icon(size: int = 24, color: str = "#FFFFFF") -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        s = size
        # Front rect
        painter.drawRoundedRect(QRectF(s * 0.3, s * 0.3, s * 0.55, s * 0.55), 2.5, 2.5)
        # Back rect outline
        back_path = QPainterPath()
        back_path.moveTo(s * 0.2, s * 0.65)
        back_path.lineTo(s * 0.2, s * 0.2)
        back_path.lineTo(s * 0.65, s * 0.2)
        painter.drawPath(back_path)

        painter.end()
        return QIcon(pix)

    @staticmethod
    def create_save_icon(size: int = 24, color: str = "#FFFFFF") -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        s = size
        # Download arrow & tray
        painter.drawLine(QPointF(s * 0.5, s * 0.2), QPointF(s * 0.5, s * 0.6))
        painter.drawLine(QPointF(s * 0.32, s * 0.44), QPointF(s * 0.5, s * 0.62))
        painter.drawLine(QPointF(s * 0.68, s * 0.44), QPointF(s * 0.5, s * 0.62))

        # Bottom tray
        tray = QPainterPath()
        tray.moveTo(s * 0.22, s * 0.6)
        tray.lineTo(s * 0.22, s * 0.78)
        tray.lineTo(s * 0.78, s * 0.78)
        tray.lineTo(s * 0.78, s * 0.6)
        painter.drawPath(tray)

        painter.end()
        return QIcon(pix)

    @staticmethod
    def create_close_icon(size: int = 24, color: str = "#FFFFFF") -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)

        s = size
        painter.drawLine(QPointF(s * 0.3, s * 0.3), QPointF(s * 0.7, s * 0.7))
        painter.drawLine(QPointF(s * 0.7, s * 0.3), QPointF(s * 0.3, s * 0.7))

        painter.end()
        return QIcon(pix)

    @staticmethod
    def create_fullscreen_icon(size: int = 24, color: str = "#FFFFFF") -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)

        s = size
        m = s * 0.25
        l = s * 0.2
        # Top-left corner
        painter.drawLine(QPointF(m, m + l), QPointF(m, m))
        painter.drawLine(QPointF(m, m), QPointF(m + l, m))
        # Top-right corner
        painter.drawLine(QPointF(s - m - l, m), QPointF(s - m, m))
        painter.drawLine(QPointF(s - m, m), QPointF(s - m, m + l))
        # Bottom-left corner
        painter.drawLine(QPointF(m, s - m - l), QPointF(m, s - m))
        painter.drawLine(QPointF(m, s - m), QPointF(m + l, s - m))
        # Bottom-right corner
        painter.drawLine(QPointF(s - m - l, s - m), QPointF(s - m, s - m))
        painter.drawLine(QPointF(s - m, s - m), QPointF(s - m, s - m - l))

        painter.end()
        return QIcon(pix)

    @staticmethod
    def create_check_icon(size: int = 24, color: str = "#FFFFFF") -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(color), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)

        s = size
        path = QPainterPath()
        path.moveTo(s * 0.22, s * 0.52)
        path.lineTo(s * 0.42, s * 0.72)
        path.lineTo(s * 0.78, s * 0.3)
        painter.drawPath(path)

        painter.end()
        return QIcon(pix)

    @staticmethod
    def create_folder_icon(size: int = 24, color: str = "#FFFFFF") -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        s = size
        path = QPainterPath()
        path.moveTo(s * 0.18, s * 0.3)
        path.lineTo(s * 0.4, s * 0.3)
        path.lineTo(s * 0.5, s * 0.4)
        path.lineTo(s * 0.82, s * 0.4)
        path.lineTo(s * 0.82, s * 0.75)
        path.lineTo(s * 0.18, s * 0.75)
        path.closeSubpath()
        painter.drawPath(path)

        painter.end()
        return QIcon(pix)

    @staticmethod
    def create_ocr_icon(size: int = 24, color: str = "#FFFFFF") -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        s = size
        # 4 Corner Scanner Brackets
        c_len = s * 0.16
        # Top-Left Bracket
        tl = QPainterPath()
        tl.moveTo(s * 0.18, s * 0.18 + c_len)
        tl.lineTo(s * 0.18, s * 0.18)
        tl.lineTo(s * 0.18 + c_len, s * 0.18)
        painter.drawPath(tl)

        # Top-Right Bracket
        tr = QPainterPath()
        tr.moveTo(s * 0.82 - c_len, s * 0.18)
        tr.lineTo(s * 0.82, s * 0.18)
        tr.lineTo(s * 0.82, s * 0.18 + c_len)
        painter.drawPath(tr)

        # Bottom-Left Bracket
        bl = QPainterPath()
        bl.moveTo(s * 0.18, s * 0.82 - c_len)
        bl.lineTo(s * 0.18, s * 0.82)
        bl.lineTo(s * 0.18 + c_len, s * 0.82)
        painter.drawPath(bl)

        # Bottom-Right Bracket
        br = QPainterPath()
        br.moveTo(s * 0.82 - c_len, s * 0.82)
        br.lineTo(s * 0.82, s * 0.82)
        br.lineTo(s * 0.82, s * 0.82 - c_len)
        painter.drawPath(br)

        # Crisp Centered 'T' (Text glyph)
        t_pen = QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(t_pen)
        # Top horizontal bar of T
        painter.drawLine(QPointF(s * 0.32, s * 0.36), QPointF(s * 0.68, s * 0.36))
        # Vertical stem of T
        painter.drawLine(QPointF(s * 0.5, s * 0.36), QPointF(s * 0.5, s * 0.68))

        painter.end()
        return QIcon(pix)
