import os
import sys
import ctypes
from enum import Enum, auto
from pathlib import Path
from PySide6.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, 
    Signal, QParallelAnimationGroup, QEvent, QObject, QRectF, QSize
)
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, 
    QFrame, QApplication, QGraphicsDropShadowEffect
)
from .styles import COLORS, TOAST_STYLE, FONT_FAMILY, get_toast_style, get_theme_tokens
from .icon_generator import IconGenerator
from ..utils.path_security import safe_open_folder

class ToastState(Enum):
    IDLE = auto()
    ENTERING = auto()
    VISIBLE = auto()
    EXITING = auto()
    CLOSED = auto()

class ToastFrame(QFrame):
    """
    Subpixel antialiased 10px rounded card frame for floating toasts.
    Eliminates non-integer DPI staircasing and border clipping.
    """
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.setObjectName("ToastFrame")
        self.setFixedHeight(38)
        self._theme = theme

    def set_theme(self, theme: str):
        self._theme = theme
        self.update()

    def sizeHint(self):
        sh = super().sizeHint()
        return QSize(sh.width(), 38)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        tokens = get_theme_tokens(self._theme)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        radius = 10.0

        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, QBrush(QColor(tokens["surface_card"])))

        border_pen = QPen(QColor(tokens["border_subtle"]), 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(border_pen)
        painter.drawPath(path)
        painter.end()

class ToastWidget(QWidget):
    """
    Ultra-compact, single-line horizontal alert pill matching shadcn/Radix minimalist inline alert:
    - Fixed height: 38px, rounded-xl 10px corners, theme-adaptive fill and border.
    - Two-layer architecture with shadow_margin = 20px for unclipped 14px ambient drop shadow.
    - Content: [16x16 circular outline status icon] + [12px medium text label].
    - Entrance: 140ms OutQuad fade & 6px vertical glide (+6px -> 0px, opacity 0.0 -> 1.0).
    - Exit: 100ms swift linear fade out (opacity 1.0 -> 0.0).
    - Repack: 160ms smooth repositioning when preceding toasts dismiss.
    """
    sig_action_clicked = Signal()
    sig_finished = Signal()

    def __init__(
        self,
        message: str,
        action_text: str = None,
        action_callback=None,
        duration_ms: int = 3000,
        variant: str = "info",
        icon_type: str = None,
        theme: str = None,
        parent=None
    ):
        super().__init__(None)

        self._state = ToastState.IDLE
        self.duration_ms = max(1000, duration_ms)
        self.action_callback = action_callback
        self._remaining_ms = self.duration_ms
        self.shadow_margin = 20

        if theme is None:
            try:
                from ..config.config_manager import ConfigManager
                self._theme = ConfigManager().get("theme", "dark")
            except Exception:
                self._theme = "dark"
        else:
            self._theme = theme

        # Two-layer composition: Root widget is transparent viewport wrapper
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setStyleSheet(get_toast_style(self._theme))

        if self.action_callback:
            self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(self.shadow_margin, self.shadow_margin, self.shadow_margin, self.shadow_margin)

        # Place all visible elements inside self.container (Two-Layer Composition)
        self.container = self.frame = ToastFrame(theme=self._theme, parent=self)

        # Ambient Drop Shadow: blur 14px, offset (0, 4)
        self.shadow = QGraphicsDropShadowEffect(self.container)
        self.shadow.setBlurRadius(14)
        if self._theme == "light":
            self.shadow.setColor(QColor(0, 0, 0, 25))
        else:
            self.shadow.setColor(QColor(0, 0, 0, 115))
        self.shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(self.shadow)

        frame_layout = QHBoxLayout(self.frame)
        frame_layout.setContentsMargins(12, 8, 16, 8)
        frame_layout.setSpacing(10)

        # Semantic Status Icon (16x16 Vector)
        v = variant or icon_type or "info"
        self.icon_label = QLabel(self.frame)
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setAlignment(Qt.AlignCenter)
        status_icon = IconGenerator.create_status_icon(v, 16)
        self.icon_label.setPixmap(status_icon.pixmap(16, 16))
        frame_layout.addWidget(self.icon_label)

        # Message Text Label
        self.msg_label = QLabel(message, self.frame)
        self.msg_label.setObjectName("ToastLabel")
        self.msg_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        frame_layout.addWidget(self.msg_label)

        layout.addWidget(self.frame)

        # Animations and Timers
        self.anim_in = None
        self.fade_in_anim = None
        self.slide_in_anim = None
        self._slide_anim = None

        self.anim_out = None
        self.fade_out_anim = None
        self.repack_anim = None

        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.start_fade_out)

    def sizeHint(self):
        f_sh = self.frame.sizeHint()
        m = self.shadow_margin
        return QSize(f_sh.width() + 2 * m, 38 + 2 * m)

    def _apply_win32_styles(self):
        """Applies native Win32 WS_EX_NOACTIVATE and WS_EX_TOOLWINDOW styles."""
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_TOPMOST = 0x00000008
                current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)
            except Exception:
                pass

    def enterEvent(self, event):
        """Pauses the dismiss timer while hovered."""
        if self._state == ToastState.VISIBLE and self.dismiss_timer.isActive():
            self._remaining_ms = self.dismiss_timer.remainingTime()
            self.dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Resumes the dismiss timer when mouse leaves."""
        if self._state == ToastState.VISIBLE and not self.dismiss_timer.isActive():
            resume_ms = max(1000, self._remaining_ms if self._remaining_ms > 0 else 1500)
            self.dismiss_timer.start(resume_ms)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.action_callback:
            self._on_action_clicked()
            return
        super().mousePressEvent(event)

    def _on_action_clicked(self):
        if self.action_callback:
            try:
                self.action_callback()
            except Exception as e:
                print(f"[Toast] Action callback error: {e}")
        self.close_toast()

    def show_toast(self, slot_index: int = 0):
        if self._state != ToastState.IDLE:
            return

        self._state = ToastState.ENTERING
        self.adjustSize()

        # Anchor strictly to screen.availableGeometry() bottom-right with shadow_margin compensation
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QApplication.primaryScreen().geometry()

        margin_bottom = 16
        margin_right = 16
        step_y = self.container.height() + 8

        target_x = avail.x() + avail.width() - self.width() + self.shadow_margin - margin_right
        base_target_y = avail.y() + avail.height() - self.height() + self.shadow_margin - margin_bottom
        target_y = base_target_y - (slot_index * step_y)
        target_pos = QPoint(target_x, target_y)

        start_pos = QPoint(target_pos.x(), target_pos.y() + 6)
        self.move(start_pos)
        self.setWindowOpacity(0.0)

        # Show without activating to protect against Windows Shell focus dismissal
        self.show()
        self._apply_win32_styles()
        self.raise_()

        # Entrance: 140ms OutQuad fade & 6px vertical glide (+6px -> 0px, opacity 0.0 -> 1.0)
        self.anim_in = QParallelAnimationGroup(self)

        self.fade_in_anim = QPropertyAnimation(self, b"windowOpacity", self.anim_in)
        self.fade_in_anim.setDuration(140)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.OutQuad)

        self.slide_in_anim = self._slide_anim = QPropertyAnimation(self, b"pos", self.anim_in)
        self.slide_in_anim.setDuration(140)
        self.slide_in_anim.setStartValue(start_pos)
        self.slide_in_anim.setEndValue(target_pos)
        self.slide_in_anim.setEasingCurve(QEasingCurve.OutQuad)

        self.anim_in.addAnimation(self.fade_in_anim)
        self.anim_in.addAnimation(self.slide_in_anim)

        self.anim_in.finished.connect(self._on_enter_finished)
        self.anim_in.start()

    def _on_enter_finished(self):
        """Starts display hold timer only after slide & fade in is completely finished."""
        if self._state == ToastState.ENTERING:
            self._state = ToastState.VISIBLE
            self.setWindowOpacity(1.0)
            self.dismiss_timer.start(self.duration_ms)

    def animate_repack(self, new_y: int):
        """Smoothly moves toast to a new vertical stack position upon other toasts dismissing (160ms OutCubic)."""
        if self._state in (ToastState.CLOSED, ToastState.EXITING):
            return

        if hasattr(self, "_slide_anim") and self._slide_anim and self._slide_anim.state() == QPropertyAnimation.Running:
            self._slide_anim.stop()
        if hasattr(self, "slide_in_anim") and self.slide_in_anim and self.slide_in_anim.state() == QPropertyAnimation.Running:
            self.slide_in_anim.stop()
        if self.anim_in and self.anim_in.state() == QParallelAnimationGroup.Running:
            self.anim_in.stop()
        if self.repack_anim and self.repack_anim.state() == QPropertyAnimation.Running:
            self.repack_anim.stop()

        target_pos = QPoint(self.pos().x(), new_y)
        self.repack_anim = QPropertyAnimation(self, b"pos")
        self.repack_anim.setDuration(160)
        self.repack_anim.setStartValue(self.pos())
        self.repack_anim.setEndValue(target_pos)
        self.repack_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.repack_anim.start()

    def start_fade_out(self):
        """Runs minimal 100ms swift linear fade out (opacity 1.0 -> 0.0), then closes strictly on finish."""
        if self._state in (ToastState.EXITING, ToastState.CLOSED):
            return

        self._state = ToastState.EXITING
        self.dismiss_timer.stop()
        if hasattr(self, "_slide_anim") and self._slide_anim and self._slide_anim.state() == QPropertyAnimation.Running:
            self._slide_anim.stop()
        if hasattr(self, "slide_in_anim") and self.slide_in_anim and self.slide_in_anim.state() == QPropertyAnimation.Running:
            self.slide_in_anim.stop()
        if self.anim_in and self.anim_in.state() == QParallelAnimationGroup.Running:
            self.anim_in.stop()
        if self.repack_anim and self.repack_anim.state() == QPropertyAnimation.Running:
            self.repack_anim.stop()

        self.anim_out = QParallelAnimationGroup(self)

        self.fade_out_anim = QPropertyAnimation(self, b"windowOpacity", self.anim_out)
        self.fade_out_anim.setDuration(100)
        self.fade_out_anim.setStartValue(self.windowOpacity())
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Linear)

        self.anim_out.addAnimation(self.fade_out_anim)
        self.anim_out.finished.connect(self.close_toast)
        self.anim_out.start()

    def fade_out(self):
        self.start_fade_out()

    def set_theme(self, theme: str):
        """Dynamically updates toast styling and drop shadow to match theme."""
        self._theme = theme
        self.frame.set_theme(theme)
        self.setStyleSheet(get_toast_style(theme))
        if hasattr(self, 'shadow') and self.shadow:
            if theme == "light":
                self.shadow.setColor(QColor(0, 0, 0, 25))
            else:
                self.shadow.setColor(QColor(0, 0, 0, 115))
        self.update()

    def close_toast(self):
        self._state = ToastState.CLOSED
        self.close()
        self.sig_finished.emit()

class ToastManager(QObject):
    """
    Singleton Manager guaranteeing persistent top-level lifecycle and vertical stack indexing for all toasts.
    """
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

    @classmethod
    def show(
        cls,
        message: str,
        variant_or_folder: str = None,
        folder_to_open: str = None,
        duration_ms: int = 3000,
        variant: str = None,
        icon_type: str = None,
        theme: str = None
    ) -> ToastWidget:
        """Standardized application-wide entry point for displaying alert toasts."""
        actual_variant = variant
        actual_folder = folder_to_open
        if variant_or_folder is not None:
            if variant_or_folder in ("info", "success", "warning", "error", "check", "copy", "ocr", "text", "folder", "app"):
                actual_variant = variant_or_folder
            else:
                actual_folder = variant_or_folder

        if not actual_variant:
            actual_variant = icon_type or "info"

        manager = cls.instance()
        return manager._show_impl(
            message=message,
            variant=actual_variant,
            folder_to_open=actual_folder,
            duration_ms=duration_ms,
            icon_type=icon_type,
            theme=theme
        )

    def __init__(self):
        super().__init__()
        self._active_toasts = []

    def _show_impl(
        self,
        message: str,
        variant: str = "info",
        folder_to_open: str = None,
        duration_ms: int = 3000,
        icon_type: str = None,
        theme: str = None
    ) -> ToastWidget:
        action_cb = None
        if folder_to_open and os.path.exists(folder_to_open):
            action_cb = lambda: safe_open_folder(folder_to_open)

        toast = ToastWidget(
            message=message,
            action_callback=action_cb,
            duration_ms=duration_ms,
            variant=variant,
            icon_type=icon_type,
            theme=theme
        )
        slot_index = len(self._active_toasts)
        self._active_toasts.append(toast)
        toast.sig_finished.connect(lambda: self._on_toast_finished(toast))
        toast.show_toast(slot_index=slot_index)
        return toast

    def _on_toast_finished(self, toast: ToastWidget):
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)

        # Repack remaining toasts smoothly into lower vertical slots
        screen = QApplication.primaryScreen()
        if screen and self._active_toasts:
            avail = screen.availableGeometry()
            margin_bottom = 16
            for i, t in enumerate(list(self._active_toasts)):
                try:
                    step_y = t.container.height() + 8
                    base_target_y = avail.y() + avail.height() - t.height() + t.shadow_margin - margin_bottom
                    new_y = base_target_y - (i * step_y)
                    t.animate_repack(new_y)
                except Exception:
                    pass

def show_quick_toast(
    message: str,
    folder_to_open: str = None,
    duration_ms: int = 3000,
    icon_type: str = None,
    variant: str = None,
    theme: str = None
) -> ToastWidget:
    """Helper to display a quick floating toast anywhere in the app."""
    return ToastManager.show(
        message=message,
        variant_or_folder=variant or icon_type or "info",
        folder_to_open=folder_to_open,
        duration_ms=duration_ms,
        icon_type=icon_type,
        theme=theme
    )
