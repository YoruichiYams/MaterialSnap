"""
Floating Action Pill for MaterialSnap screenshot overlay.
Built with Origin UI styling:
- Solid dark #161719 background, 1px solid #2A2D32, border-radius 12px, shadow_margin 16px.
- Action Pill buttons: border-radius 8px, border 1px solid #2D3035, background #1E1F22,
  padding 6px 12px, text #E0E0E0.
  Hover: #26282D, border #3D424A, text #FFFFFF.
  Pressed: #2F333A, border #454B54, text #FFFFFF.
- Smooth 140ms OutCubic entry (+4px translation) and 100ms Linear exit fade.
"""

from PySide6.QtCore import (
    Qt, QRect, QPoint, Signal, QSize, QPropertyAnimation, QEasingCurve, 
    QEvent, QParallelAnimationGroup
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QFrame, QApplication, 
    QGraphicsDropShadowEffect
)
from .styles import COLORS, FONT_FAMILY, get_pill_style

class ActionButton(QToolButton):
    """
    Shadcn/Radix Segmented Action Button with text-only label, subtle hover/pressed states,
    and suppressed tooltip popups.
    """
    def __init__(self, text: str = "", position: str = "middle", parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPillButton")
        self.setProperty("position", position)
        self.btn_text = text
        self.setText(text)
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(32)

    def event(self, e):
        # Completely block standard tooltip event popups
        if e.type() == QEvent.ToolTip:
            return True
        return super().event(e)

class PillFrame(QFrame):
    """
    Unified segmented container frame housing the attached outline action buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPillFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)

class ActionPillWidget(QWidget):
    """
    MaterialSnap floating action pill with shadcn/Radix segmented styling and zero tooltips.
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
        self.shadow_margin = 20

        self._entry_anim_group = None
        self._exit_anim = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(self.shadow_margin, self.shadow_margin, self.shadow_margin, self.shadow_margin)

        # Place all visible elements inside self.container (Two-Layer Composition)
        self.container = self.frame = PillFrame(self)

        # Floating elevation drop shadow attached to self.container, diffusing cleanly within margin
        self.shadow = QGraphicsDropShadowEffect(self.container)
        self.shadow.setBlurRadius(14)
        self.shadow.setColor(QColor(0, 0, 0, 140))
        self.shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(self.shadow)

        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. OCR / Text Extraction Button
        self.btn_ocr = ActionButton("Text", position="first", parent=self.frame)
        self.btn_ocr.clicked.connect(self.sig_ocr.emit)
        layout.addWidget(self.btn_ocr)
        self.frame.btn_ocr = self.btn_ocr

        # 2. Copy Button
        self.btn_copy = ActionButton("Copy", position="middle", parent=self.frame)
        self.btn_copy.clicked.connect(self.sig_copy.emit)
        layout.addWidget(self.btn_copy)
        self.frame.btn_copy = self.btn_copy

        # 3. Save Button
        self.btn_save = ActionButton("Save", position="middle", parent=self.frame)
        self.btn_save.clicked.connect(lambda: self._on_save_clicked(False))
        self.btn_save.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_save.customContextMenuRequested.connect(lambda _: self._on_save_clicked(True))
        layout.addWidget(self.btn_save)
        self.frame.btn_save = self.btn_save

        # 4. Fullscreen Quick Button
        self.btn_full = ActionButton("Full", position="middle", parent=self.frame)
        self.btn_full.clicked.connect(self.sig_fullscreen.emit)
        layout.addWidget(self.btn_full)
        self.frame.btn_full = self.btn_full

        # 5. Cancel / Close Button
        self.btn_cancel = ActionButton("Close", position="last", parent=self.frame)
        self.btn_cancel.clicked.connect(self.sig_cancel.emit)
        layout.addWidget(self.btn_cancel)
        self.frame.btn_cancel = self.btn_cancel

        main_layout.addWidget(self.frame)

        self.buttons = [self.btn_ocr, self.btn_copy, self.btn_save, self.btn_full, self.btn_cancel]
        self.set_theme("dark")

    def set_theme(self, theme: str):
        """Dynamically applies dark or light theme styles and adjusts elevation shadow."""
        self._theme = theme
        self.setStyleSheet(get_pill_style(theme))
        if hasattr(self, 'shadow') and self.shadow:
            if theme == "light":
                self.shadow.setColor(QColor(0, 0, 0, 25))
            else:
                self.shadow.setColor(QColor(0, 0, 0, 140))
        self.update()

    def _on_save_clicked(self, prompt_override: bool):
        modifiers = QApplication.keyboardModifiers()
        prompt = prompt_override or bool(modifiers & Qt.ShiftModifier)
        self.sig_save.emit(prompt)

    def position_smartly(self, selection_rect: QRect, container_bounds: QRect):
        """
        Dynamically places the pill relative to selection while keeping inside container_bounds,
        animating smoothly into view with a 140ms OutCubic entrance.
        """
        sh = self.sizeHint()
        pw = max(sh.width(), self.width()) if sh.isValid() else max(300, self.width())
        ph = max(sh.height(), self.height()) if sh.isValid() else max(48, self.height())
        self.resize(pw, ph)
        m = self.shadow_margin

        # Visual frame dimensions
        cw = pw - 2 * m
        ch = ph - 2 * m

        # Desired visual container position relative to selection_rect
        vx = selection_rect.right() - cw + 2
        vy = selection_rect.bottom() + 10

        # Flip above selection if overflowing bottom
        if vy + ch > container_bounds.bottom() - 10:
            vy = selection_rect.top() - ch - 10

        # Flip below if overflowing top
        if vy < container_bounds.top() + 10:
            vy = selection_rect.bottom() + 10

        # Convert to root widget coordinates with shadow_margin
        target_x = vx - m
        target_y = vy - m

        # Clamp root widget inside container_bounds (keeps shadow halo and root widget strictly inside bounds)
        max_x = max(container_bounds.left(), container_bounds.right() - pw)
        max_y = max(container_bounds.top(), container_bounds.bottom() - ph)
        target_x = max(container_bounds.left(), min(target_x, max_x))
        target_y = max(container_bounds.top(), min(target_y, max_y))

        # Stop any active hide animation
        if self._exit_anim and self._exit_anim.state() == QPropertyAnimation.Running:
            self._exit_anim.stop()

        start_pos = QPoint(target_x, target_y + 4)
        target_pos = QPoint(target_x, target_y)

        self.move(start_pos)
        self.show()
        self.raise_()

        # Origin UI Minimal Micro-Transition: 140ms OutCubic (+4px to 0px, 0.0 to 1.0)
        self._entry_anim_group = QParallelAnimationGroup(self)

        pos_anim = QPropertyAnimation(self, b"pos", self._entry_anim_group)
        pos_anim.setDuration(140)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(target_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        fade_anim = QPropertyAnimation(self, b"windowOpacity", self._entry_anim_group)
        fade_anim.setDuration(140)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._entry_anim_group.addAnimation(pos_anim)
        self._entry_anim_group.addAnimation(fade_anim)
        self._entry_anim_group.finished.connect(lambda: self.setWindowOpacity(1.0))
        self._entry_anim_group.start()

    def animate_hide(self, on_finished=None):
        """Instant minimal 100ms linear fade out (1.0 to 0.0)."""
        if not self.isVisible():
            if on_finished:
                on_finished()
            return

        if self._entry_anim_group and self._entry_anim_group.state() == QParallelAnimationGroup.Running:
            self._entry_anim_group.stop()

        self._exit_anim = QPropertyAnimation(self, b"windowOpacity")
        self._exit_anim.setDuration(100)
        self._exit_anim.setStartValue(self.windowOpacity())
        self._exit_anim.setEndValue(0.0)
        self._exit_anim.setEasingCurve(QEasingCurve.Linear)

        def _on_done():
            self.hide()
            self.setWindowOpacity(1.0)
            if on_finished:
                on_finished()

        self._exit_anim.finished.connect(_on_done)
        self._exit_anim.start()
