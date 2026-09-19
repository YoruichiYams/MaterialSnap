import math
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QRectF, QPointF, QSize
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath

class ThemeToggle(QWidget):
    """
    Interactive shadcn/Radix-style ThemeToggle capsule widget:
    - Fixed size: 64px width, 32px height.
    - Track: fully rounded capsule (border-radius: 16px).
    - Sliding thumb: 24px x 24px circular badge with 220ms OutCubic animation.
    - Icons: Lucide Moon (dark) & Lucide Sun (light).
    - Signal: sig_theme_changed(str) -> "dark" | "light"
    """
    sig_theme_changed = Signal(str)

    def __init__(self, initial_theme: str = "dark", parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)

        self._is_dark = (initial_theme != "light")
        self._thumb_x = 4.0 if self._is_dark else 36.0

        self._anim = QPropertyAnimation(self, b"thumb_x")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    @Property(float)
    def thumb_x(self) -> float:
        return self._thumb_x

    @thumb_x.setter
    def thumb_x(self, val: float):
        self._thumb_x = float(val)
        self.update()

    def is_dark(self) -> bool:
        return self._is_dark

    def set_is_dark(self, is_dark: bool, animate: bool = True):
        target_x = 4.0 if is_dark else 36.0
        if self._is_dark == is_dark and self._thumb_x == target_x:
            return
        self._is_dark = is_dark
        if animate:
            if self._anim.state() == QPropertyAnimation.Running:
                self._anim.stop()
            self._anim.setStartValue(self._thumb_x)
            self._anim.setEndValue(target_x)
            self._anim.start()
        else:
            if self._anim.state() == QPropertyAnimation.Running:
                self._anim.stop()
            self.thumb_x = target_x

    def set_theme(self, theme: str, animate: bool = False):
        self.set_is_dark(theme != "light", animate=animate)

    def toggle(self):
        new_is_dark = not self._is_dark
        self.set_is_dark(new_is_dark, animate=True)
        self.sig_theme_changed.emit("dark" if new_is_dark else "light")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
            event.accept()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _draw_moon_icon(self, painter: QPainter, cx: float, cy: float, color: QColor):
        painter.save()
        pen = QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        path = QPainterPath()
        path.moveTo(cx + 4.2, cy + 0.4)
        path.cubicTo(cx + 4.2, cy + 4.0, cx + 1.0, cy + 5.0, cx - 1.2, cy + 4.6)
        path.cubicTo(cx - 4.0, cy + 4.0, cx - 5.0, cy + 1.2, cx - 4.6, cy - 1.5)
        path.cubicTo(cx - 4.0, cy - 3.8, cx - 2.0, cy - 4.6, cx - 0.4, cy - 4.6)
        path.cubicTo(cx - 1.0, cy - 2.8, cx - 0.6, cy - 1.0, cx + 0.6, cy + 0.2)
        path.cubicTo(cx + 1.8, cy + 1.0, cx + 3.2, cy + 1.0, cx + 4.2, cy + 0.4)
        painter.drawPath(path)
        painter.restore()

    def _draw_sun_icon(self, painter: QPainter, cx: float, cy: float, color: QColor):
        painter.save()
        pen = QPen(color, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Center circle
        painter.drawEllipse(QPointF(cx, cy), 2.5, 2.5)

        # 8 rays
        for i in range(8):
            angle = i * (math.pi / 4.0)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            p1 = QPointF(cx + cos_a * 4.0, cy + sin_a * 4.0)
            p2 = QPointF(cx + cos_a * 5.8, cy + sin_a * 5.8)
            painter.drawLine(p1, p2)
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Fraction of transition: 0.0 (dark) to 1.0 (light)
        progress = max(0.0, min(1.0, (self._thumb_x - 4.0) / 32.0))

        # 1. Outer Track
        track_rect = QRectF(0.5, 0.5, 63.0, 31.0)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, 15.5, 15.5)

        # Interpolate track background: #09090B (dark) -> #FFFFFF (light)
        bg_r = int(9 + (255 - 9) * progress)
        bg_g = int(9 + (255 - 9) * progress)
        bg_b = int(11 + (255 - 11) * progress)
        painter.fillPath(track_path, QColor(bg_r, bg_g, bg_b))

        # Interpolate track border: #27272A (dark) -> #E4E4E7 (light)
        br_r = int(39 + (228 - 39) * progress)
        br_g = int(39 + (228 - 39) * progress)
        br_b = int(42 + (231 - 42) * progress)
        painter.setPen(QPen(QColor(br_r, br_g, br_b), 1.0))
        painter.drawPath(track_path)

        # Focus ring when keyboard focused
        if self.hasFocus():
            painter.setPen(QPen(QColor("#4E54D4"), 1.5))
            painter.drawPath(track_path)

        # 2. Inactive Icons in Track
        inactive_color = QColor("#71717A")
        # Inactive Moon at left track center (16, 16)
        self._draw_moon_icon(painter, 16.0, 16.0, inactive_color)
        # Inactive Sun at right track center (48, 16)
        self._draw_sun_icon(painter, 48.0, 16.0, inactive_color)

        # 3. Sliding Thumb
        thumb_rect = QRectF(self._thumb_x, 4.0, 24.0, 24.0)
        thumb_path = QPainterPath()
        thumb_path.addRoundedRect(thumb_rect, 12.0, 12.0)

        # Interpolate thumb background: #27272A (dark) -> #E4E4E7 (light)
        th_r = int(39 + (228 - 39) * progress)
        th_g = int(39 + (228 - 39) * progress)
        th_b = int(42 + (231 - 42) * progress)
        painter.fillPath(thumb_path, QColor(th_r, th_g, th_b))

        # 4. Active Icon inside Thumb
        thumb_cx = self._thumb_x + 12.0
        thumb_cy = 16.0

        if progress < 0.5:
            # Active Moon icon (pure white) with fade
            alpha = int(255 * (1.0 - progress * 2.0))
            self._draw_moon_icon(painter, thumb_cx, thumb_cy, QColor(255, 255, 255, alpha))
        else:
            # Active Sun icon (dark charcoal #27272A) with fade
            alpha = int(255 * ((progress - 0.5) * 2.0))
            self._draw_sun_icon(painter, thumb_cx, thumb_cy, QColor(39, 39, 42, alpha))

        painter.end()
