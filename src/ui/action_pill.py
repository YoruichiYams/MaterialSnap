import math
from PySide6.QtCore import (
    Qt, QRect, QPoint, Signal, QSize, QPropertyAnimation, QEasingCurve, 
    QEvent, Property, QVariantAnimation
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QKeySequence, QFont, 
    QCursor, QPixmap, QFontMetrics
)
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QFrame, QLabel, QApplication, 
    QGraphicsDropShadowEffect
)
from .styles import COLORS, FONT_FAMILY
from .icon_generator import IconGenerator

class ActionButton(QToolButton):
    """
    Transparent event-capturing hit target for action pill buttons.
    Delegates all visual rendering to the dual-layer PillFrame canvas.
    Completely disables any tooltip popup events.
    """
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.btn_text = text
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setMouseTracking(True)
        # Transparent background and invisible text (rendered by PillFrame)
        self.setStyleSheet("background: transparent; border: none; color: transparent;")

    def event(self, e):
        # Completely block standard tooltip event popups
        if e.type() == QEvent.ToolTip:
            return True
        return super().event(e)

    def paintEvent(self, event):
        # Pass-through: PillFrame handles dual-layer masked rendering
        pass

class PillFrame(QFrame):
    """
    Custom-painted capsule frame with Dual-Layer Masked text/icon inversion
    and elastic stretching sliding hover highlight.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPillFrame")
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self._indicator_rect = QRect()
        self._start_rect = QRect()
        self._target_rect = QRect()
        self._indicator_opacity = 0.0

        self._stretch_anim = None
        self._fade_anim = None

        # Pre-cached icons for ultra-fast dual-layer rendering
        self._cache_icons()

    def _cache_icons(self):
        """Pre-renders white and dark vector icons as QPixmaps."""
        self.icons = {
            "ocr_white": IconGenerator.create_ocr_icon(18, "#FFFFFF").pixmap(QSize(18, 18)),
            "ocr_dark": IconGenerator.create_ocr_icon(18, "#161719").pixmap(QSize(18, 18)),
            "copy_white": IconGenerator.create_copy_icon(18, "#FFFFFF").pixmap(QSize(18, 18)),
            "copy_dark": IconGenerator.create_copy_icon(18, "#161719").pixmap(QSize(18, 18)),
            "save_white": IconGenerator.create_save_icon(18, "#FFFFFF").pixmap(QSize(18, 18)),
            "save_dark": IconGenerator.create_save_icon(18, "#161719").pixmap(QSize(18, 18)),
            "full_white": IconGenerator.create_fullscreen_icon(18, "#FFFFFF").pixmap(QSize(18, 18)),
            "full_dark": IconGenerator.create_fullscreen_icon(18, "#161719").pixmap(QSize(18, 18)),
            "close_white": IconGenerator.create_close_icon(18, "#FFFFFF").pixmap(QSize(18, 18)),
            "close_dark": IconGenerator.create_close_icon(18, "#161719").pixmap(QSize(18, 18)),
        }

    def get_indicator_opacity(self) -> float:
        return self._indicator_opacity

    def set_indicator_opacity(self, val: float):
        self._indicator_opacity = val
        self.update()

    indicator_opacity = Property(float, get_indicator_opacity, set_indicator_opacity)

    def animate_stretch_to(self, target_rect: QRect):
        """
        Animates the indicator to target_rect with a 2-phase elastic stretch.
        Always uses the current rendered rect to eliminate reverse-stretch glitches.
        """
        if not self._indicator_rect.isValid() or self._indicator_opacity < 0.05:
            self._indicator_rect = QRect(target_rect)
            self._start_rect = QRect(target_rect)
            self._target_rect = QRect(target_rect)
            self.update()
        else:
            if self._stretch_anim and self._stretch_anim.state() == QVariantAnimation.Running:
                self._stretch_anim.stop()

            self._start_rect = QRect(self._indicator_rect)
            self._target_rect = QRect(target_rect)

            if self._start_rect != self._target_rect:
                self._stretch_anim = QVariantAnimation(self)
                self._stretch_anim.setDuration(190)
                self._stretch_anim.setStartValue(0.0)
                self._stretch_anim.setEndValue(1.0)
                self._stretch_anim.valueChanged.connect(self._on_stretch_step)
                self._stretch_anim.start()

        # Fade in if not fully visible
        if self._indicator_opacity < 0.95:
            if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
                self._fade_anim.stop()
            self._fade_anim = QPropertyAnimation(self, b"indicator_opacity")
            self._fade_anim.setDuration(130)
            self._fade_anim.setStartValue(self._indicator_opacity)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.OutQuad)
            self._fade_anim.start()

    def _on_stretch_step(self, t: float):
        """Calculates elastic stretched bounding box at progress t in [0.0, 1.0]."""
        x1_start = self._start_rect.left()
        x2_start = self._start_rect.right()
        x1_end = self._target_rect.left()
        x2_end = self._target_rect.right()

        moving_right = x1_end >= x1_start

        # Fluid cubic easing for stretch-and-snap effect
        t_lead = 1.0 - math.pow(1.0 - t, 3)
        t_trail = math.pow(t, 2.5)

        if moving_right:
            cur_right = int(x2_start + (x2_end - x2_start) * t_lead)
            cur_left = int(x1_start + (x1_end - x1_start) * t_trail)
        else:
            cur_left = int(x1_start + (x1_end - x1_start) * t_lead)
            cur_right = int(x2_start + (x2_end - x2_start) * t_trail)

        y = self._target_rect.top()
        h = self._target_rect.height()
        w = max(cur_right - cur_left + 1, self._target_rect.width())

        self._indicator_rect = QRect(cur_left, y, w, h)
        self.update()

    def fade_out(self):
        """Fades out indicator smoothly when mouse leaves."""
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()

        self._fade_anim = QPropertyAnimation(self, b"indicator_opacity")
        self._fade_anim.setDuration(170)
        self._fade_anim.setStartValue(self._indicator_opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InQuad)
        self._fade_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 1. Main Dark Capsule Background
        pill_rect = self.rect()
        pill_radius = pill_rect.height() / 2.0
        
        container_path = QPainterPath()
        container_path.addRoundedRect(pill_rect, pill_radius, pill_radius)
        painter.fillPath(container_path, QBrush(QColor(22, 23, 25, 235)))

        # Subtle divider line
        if hasattr(self, 'divider') and self.divider.isVisible():
            div_rect = self.divider.geometry()
            div_cx = div_rect.center().x()
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
            painter.drawLine(div_cx, 13, div_cx, self.height() - 13)

        # 2. Base Layer: Pure White Text & Icons (#FFFFFF)
        self._draw_content_layer(painter, is_dark=False)

        # 3. Highlight Pill & Clipped Inverted Dark Layer (#1E1F22)
        if self._indicator_opacity > 0.001 and self._indicator_rect.isValid():
            r = self._indicator_rect
            ind_radius = r.height() / 2.0
            
            # Pill capsule clipping path
            clip_path = QPainterPath()
            clip_path.addRoundedRect(r, ind_radius, ind_radius)

            # Draw Solid White Sliding Highlight Pill
            ind_color = QColor(255, 255, 255, int(255 * self._indicator_opacity))
            painter.fillPath(clip_path, QBrush(ind_color))

            # Draw Masked Inverted Dark Content (Strictly clipped to indicator pill)
            painter.save()
            painter.setClipPath(clip_path)
            painter.setOpacity(self._indicator_opacity)
            self._draw_content_layer(painter, is_dark=True)
            painter.restore()

        painter.end()

    def _draw_content_layer(self, painter: QPainter, is_dark: bool):
        """
        Renders all button labels and icons in either pure white (#FFFFFF) or dark charcoal (#1E1F22).
        """
        color_str = "#161719" if is_dark else "#FFFFFF"
        text_color = QColor(color_str)

        font = QFont("Google Sans Flex", 10, QFont.Bold if is_dark else QFont.DemiBold)
        font.setStyleHint(QFont.SansSerif)
        painter.setFont(font)
        fm = painter.fontMetrics()

        items = [
            (getattr(self, 'btn_ocr', None), "ocr", "Text"),
            (getattr(self, 'btn_copy', None), "copy", "Copy"),
            (getattr(self, 'btn_save', None), "save", "Save"),
            (getattr(self, 'btn_full', None), "full", ""),
            (getattr(self, 'btn_cancel', None), "close", ""),
        ]

        for btn, icon_key, text in items:
            if not btn or not btn.isVisible():
                continue

            r = btn.geometry()
            icon_pix = self.icons[f"{icon_key}_{'dark' if is_dark else 'white'}"]

            if text:
                text_w = fm.horizontalAdvance(text)
                total_w = 18 + 6 + text_w
                start_x = r.left() + (r.width() - total_w) / 2
                
                # Draw Icon
                icon_y = r.top() + (r.height() - 18) / 2
                painter.drawPixmap(int(start_x), int(icon_y), icon_pix)

                # Draw Text Label
                text_rect = QRect(int(start_x + 18 + 6), r.top(), int(text_w + 4), r.height())
                painter.setPen(text_color)
                painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)
            else:
                # Icon-only button (Full screen / Cancel)
                icon_x = r.left() + (r.width() - 18) / 2
                icon_y = r.top() + (r.height() - 18) / 2
                painter.drawPixmap(int(icon_x), int(icon_y), icon_pix)

class ActionPillWidget(QWidget):
    """
    Material You floating action pill with dual-layer masked color inversion and zero tooltips.
    """
    sig_ocr = Signal()
    sig_copy = Signal()
    sig_save = Signal(bool)
    sig_fullscreen = Signal()
    sig_cancel = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self._hovered_btn = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # Dual-Layer Canvas Frame
        self.frame = PillFrame(self)

        # Floating elevation drop shadow
        shadow = QGraphicsDropShadowEffect(self.frame)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 5)
        self.frame.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        # 1. OCR / Text Extraction Button (No Tooltips)
        self.btn_ocr = ActionButton("Text", self.frame)
        self.btn_ocr.setMinimumWidth(72)
        self.btn_ocr.clicked.connect(self.sig_ocr.emit)
        layout.addWidget(self.btn_ocr)
        self.frame.btn_ocr = self.btn_ocr

        # 2. Copy Button (No Tooltips)
        self.btn_copy = ActionButton("Copy", self.frame)
        self.btn_copy.setMinimumWidth(72)
        self.btn_copy.clicked.connect(self.sig_copy.emit)
        layout.addWidget(self.btn_copy)
        self.frame.btn_copy = self.btn_copy

        # 3. Save Button (No Tooltips)
        self.btn_save = ActionButton("Save", self.frame)
        self.btn_save.setMinimumWidth(72)
        self.btn_save.clicked.connect(lambda: self._on_save_clicked(False))
        self.btn_save.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_save.customContextMenuRequested.connect(lambda _: self._on_save_clicked(True))
        layout.addWidget(self.btn_save)
        self.frame.btn_save = self.btn_save

        # Divider Frame
        self.divider = QFrame(self.frame)
        self.divider.setObjectName("PillDivider")
        self.divider.setFixedWidth(6)
        self.divider.setFixedHeight(20)
        self.divider.setCursor(Qt.PointingHandCursor)
        self.divider.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.divider)
        self.frame.divider = self.divider

        # 4. Fullscreen Quick Button (No Tooltips)
        self.btn_full = ActionButton("", self.frame)
        self.btn_full.setMinimumWidth(38)
        self.btn_full.clicked.connect(self.sig_fullscreen.emit)
        layout.addWidget(self.btn_full)
        self.frame.btn_full = self.btn_full

        # 5. Cancel Button (No Tooltips)
        self.btn_cancel = ActionButton("", self.frame)
        self.btn_cancel.setMinimumWidth(38)
        self.btn_cancel.clicked.connect(self.sig_cancel.emit)
        layout.addWidget(self.btn_cancel)
        self.frame.btn_cancel = self.btn_cancel

        main_layout.addWidget(self.frame)

        # Event filtering for motion tracking and blocking tooltip popups
        self.buttons = [self.btn_ocr, self.btn_copy, self.btn_save, self.btn_full, self.btn_cancel]
        for btn in self.buttons:
            btn.installEventFilter(self)
        self.frame.installEventFilter(self)

    def eventFilter(self, watched, event):
        # Completely suppress any tooltip events
        if event.type() == QEvent.ToolTip:
            return True

        if event.type() == QEvent.Enter:
            if watched in self.buttons:
                self._slide_to_button(watched)
                return False
        elif event.type() == QEvent.MouseMove:
            if watched == self.frame:
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                self._handle_frame_mouse_move(pos)
        elif event.type() == QEvent.Leave:
            if watched == self.frame:
                pos = self.frame.mapFromGlobal(QApplication.mousePosition().toPoint())
                if not self.frame.rect().contains(pos):
                    self._fade_out_indicator()
        return super().eventFilter(watched, event)

    def _handle_frame_mouse_move(self, local_pos: QPoint):
        """Finds closest button under cursor even across zero-space seams."""
        for btn in self.buttons:
            if btn.geometry().contains(local_pos):
                if self._hovered_btn != btn:
                    self._slide_to_button(btn)
                return

    def _slide_to_button(self, target_btn: ActionButton):
        """Animates elastic stretching indicator to target button."""
        self._hovered_btn = target_btn
        target_rect = target_btn.geometry()
        self.frame.animate_stretch_to(target_rect)

    def _fade_out_indicator(self):
        """Fades out indicator smoothly on exit."""
        self._hovered_btn = None
        self.frame.fade_out()

    def _on_save_clicked(self, prompt_override: bool):
        modifiers = QApplication.keyboardModifiers()
        prompt = prompt_override or bool(modifiers & Qt.ShiftModifier)
        self.sig_save.emit(prompt)

    def position_smartly(self, selection_rect: QRect, container_bounds: QRect):
        """
        Dynamically places the pill relative to selection while keeping inside container_bounds.
        """
        self.adjustSize()
        pw = self.width()
        ph = self.height()

        target_x = selection_rect.right() - pw + 8
        target_y = selection_rect.bottom() + 10

        if target_y + ph > container_bounds.bottom() - 10:
            target_y = selection_rect.top() - ph - 10

        if target_y < container_bounds.top() + 10:
            target_y = selection_rect.bottom() - ph - 10

        if target_x + pw > container_bounds.right() - 10:
            target_x = container_bounds.right() - pw - 10
        if target_x < container_bounds.left() + 10:
            target_x = container_bounds.left() + 10

        self.move(target_x, target_y)
        self.show()
        self.raise_()
