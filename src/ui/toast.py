import os
import sys
import ctypes
from enum import Enum, auto
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, Signal, QParallelAnimationGroup, QEvent, QObject
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, 
    QFrame, QApplication, QGraphicsDropShadowEffect
)
from .styles import COLORS, TOAST_STYLE, FONT_FAMILY
from .icon_generator import IconGenerator
from ..utils.path_security import safe_open_folder

class ToastState(Enum):
    IDLE = auto()
    ENTERING = auto()
    VISIBLE = auto()
    EXITING = auto()
    CLOSED = auto()

class ToastWidget(QWidget):
    """
    Sleek floating toast notification pill with frosted glass dark matte background,
    state-machine deterministic lifecycle, and native Win32 WS_EX_NOACTIVATE / ToolTip flags.
    """
    sig_action_clicked = Signal()
    sig_finished = Signal()

    def __init__(self, message: str, action_text: str = None, action_callback=None, duration_ms: int = 3000, icon_type: str = "check", parent=None):
        super().__init__(None)
        
        self._state = ToastState.IDLE
        self.duration_ms = max(1000, duration_ms)
        self.action_callback = action_callback
        self._remaining_ms = self.duration_ms

        # ToolTip + Frameless + StaysOnTop prevents OS subwindow destruction & focus stealing
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setStyleSheet(TOAST_STYLE)

        if self.action_callback:
            self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Main Capsule Pill Frame
        self.frame = QFrame(self)
        self.frame.setObjectName("ToastFrame")
        self.frame.setFixedHeight(44)

        # Deep ambient drop shadow for elevation
        shadow = QGraphicsDropShadowEffect(self.frame)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.frame.setGraphicsEffect(shadow)

        frame_layout = QHBoxLayout(self.frame)
        frame_layout.setContentsMargins(16, 6, 16, 6)
        frame_layout.setSpacing(10)

        # Monochromatic Minimal Vector Icon
        self.icon_label = QLabel(self.frame)
        if icon_type == "folder":
            pix = IconGenerator.create_folder_icon(18, "#FFFFFF").pixmap(18, 18)
        elif icon_type == "copy":
            pix = IconGenerator.create_copy_icon(18, "#FFFFFF").pixmap(18, 18)
        elif icon_type in ("ocr", "text"):
            pix = IconGenerator.create_ocr_icon(18, "#FFFFFF").pixmap(18, 18)
        elif icon_type == "app":
            pix = IconGenerator.create_app_icon(18).pixmap(18, 18)
        else:
            pix = IconGenerator.create_check_icon(18, "#FFFFFF").pixmap(18, 18)
        self.icon_label.setPixmap(pix)
        frame_layout.addWidget(self.icon_label)

        # Message Text
        self.msg_label = QLabel(message, self.frame)
        self.msg_label.setObjectName("ToastLabel")
        frame_layout.addWidget(self.msg_label)

        # Optional Action Button (e.g. "Open Folder")
        if action_text and action_callback:
            self.action_btn = QToolButton(self.frame)
            self.action_btn.setText(action_text)
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.setStyleSheet(f"""
                QToolButton {{
                    color: #FFFFFF;
                    background-color: rgba(255, 255, 255, 0.10);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 9999px;
                    padding: 4px 14px;
                    font-family: {FONT_FAMILY};
                    font-weight: 600;
                    font-size: 12px;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.20);
                    border-color: rgba(255, 255, 255, 0.25);
                    color: #FFFFFF;
                }}
            """)
            self.action_btn.clicked.connect(self._on_action_clicked)
            frame_layout.addWidget(self.action_btn)

        layout.addWidget(self.frame)

        # Animations and Timers
        self.anim_in = None
        self.fade_in_anim = None
        self.slide_in_anim = None

        self.anim_out = None
        self.fade_out_anim = None
        self.slide_out_anim = None

        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.start_fade_out)

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

    def show_toast(self):
        if self._state != ToastState.IDLE:
            return

        self._state = ToastState.ENTERING
        self.adjustSize()
        
        # Anchor strictly to the bottom-right corner of the primary screen
        screen = QApplication.primaryScreen()
        target_pos = QPoint(100, 100)
        if screen:
            screen_geo = screen.geometry()
            target_x = screen_geo.x() + screen_geo.width() - self.width() - 24
            target_y = screen_geo.y() + screen_geo.height() - self.height() - 60
            target_pos = QPoint(target_x, target_y)

        start_pos = QPoint(target_pos.x(), target_pos.y() + 16)
        self.move(start_pos)
        self.setWindowOpacity(0.0)

        # Show without activating to protect against Windows Shell focus dismissal
        self.show()
        self._apply_win32_styles()
        self.raise_()

        # Step 1: Slide Up + Fade In (300ms, OutCubic)
        self.anim_in = QParallelAnimationGroup(self)

        self.fade_in_anim = QPropertyAnimation(self, b"windowOpacity", self.anim_in)
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.slide_in_anim = QPropertyAnimation(self, b"pos", self.anim_in)
        self.slide_in_anim.setDuration(300)
        self.slide_in_anim.setStartValue(start_pos)
        self.slide_in_anim.setEndValue(target_pos)
        self.slide_in_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.anim_in.addAnimation(self.fade_in_anim)
        self.anim_in.addAnimation(self.slide_in_anim)

        # Step 2: Start hold timer for 3.0s ONLY AFTER enter animation finishes
        self.anim_in.finished.connect(self._on_enter_finished)
        self.anim_in.start()

    def _on_enter_finished(self):
        """Starts display hold timer only after slide & fade in is completely finished."""
        if self._state == ToastState.ENTERING:
            self._state = ToastState.VISIBLE
            self.setWindowOpacity(1.0)
            self.dismiss_timer.start(self.duration_ms)

    def start_fade_out(self):
        """Runs fade out and slide down animation, then closes strictly on finish."""
        if self._state in (ToastState.EXITING, ToastState.CLOSED):
            return

        self._state = ToastState.EXITING
        self.dismiss_timer.stop()
        if self.anim_in and self.anim_in.state() == QParallelAnimationGroup.Running:
            self.anim_in.stop()

        cur_pos = self.pos()
        target_pos = QPoint(cur_pos.x(), cur_pos.y() + 12)

        self.anim_out = QParallelAnimationGroup(self)

        self.fade_out_anim = QPropertyAnimation(self, b"windowOpacity", self.anim_out)
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(self.windowOpacity())
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.InCubic)

        self.slide_out_anim = QPropertyAnimation(self, b"pos", self.anim_out)
        self.slide_out_anim.setDuration(300)
        self.slide_out_anim.setStartValue(cur_pos)
        self.slide_out_anim.setEndValue(target_pos)
        self.slide_out_anim.setEasingCurve(QEasingCurve.InCubic)

        self.anim_out.addAnimation(self.fade_out_anim)
        self.anim_out.addAnimation(self.slide_out_anim)

        self.anim_out.finished.connect(self.close_toast)
        self.anim_out.start()

    def fade_out(self):
        self.start_fade_out()

    def close_toast(self):
        self._state = ToastState.CLOSED
        self.close()
        self.sig_finished.emit()

class ToastManager(QObject):
    """
    Singleton Manager guaranteeing persistent top-level lifecycle for all toasts.
    """
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._active_toasts = []

    def show(self, message: str, folder_to_open: str = None, duration_ms: int = 3000, icon_type: str = "check") -> ToastWidget:
        action_cb = None
        action_label = None
        if folder_to_open and os.path.exists(folder_to_open):
            action_label = "Open Folder"
            action_cb = lambda: safe_open_folder(folder_to_open)

        toast = ToastWidget(message, action_text=action_label, action_callback=action_cb, duration_ms=duration_ms, icon_type=icon_type)
        self._active_toasts.append(toast)
        toast.sig_finished.connect(lambda: self._on_toast_finished(toast))
        toast.show_toast()
        return toast

    def _on_toast_finished(self, toast: ToastWidget):
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)

def show_quick_toast(message: str, folder_to_open: str = None, duration_ms: int = 3000, icon_type: str = "check") -> ToastWidget:
    """Helper to display a quick floating toast anywhere in the app."""
    return ToastManager.instance().show(message, folder_to_open=folder_to_open, duration_ms=duration_ms, icon_type=icon_type)
