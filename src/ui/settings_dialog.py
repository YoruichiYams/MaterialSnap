from pathlib import Path
from PySide6.QtCore import Qt, Signal, QRectF, QPoint, QPointF, QSize, QEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QCheckBox, QComboBox, QFileDialog, QFrame, QWidget, QGraphicsDropShadowEffect,
    QToolButton, QStyledItemDelegate, QStyle, QApplication
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QPen, QBrush, QKeySequence, 
    QCursor, QMouseEvent, QKeyEvent
)
from .styles import (
    get_settings_dialog_style, get_application_stylesheet, get_theme_tokens,
    FONT_FAMILY, SETTINGS_DIALOG_STYLE
)
from .theme_toggle import ThemeToggle
from .icon_generator import IconGenerator
from ..utils.autostart import is_autostart_enabled, set_autostart
from ..config.themes import WAVE_THEMES, DEFAULT_WAVE_THEME, get_wave_palette

class DraggableTitleBar(QWidget):
    """
    Titlebar widget supporting mouse dragging to reposition the frameless dialog.
    """
    def __init__(self, dialog=None, parent=None):
        super().__init__(parent or (dialog if isinstance(dialog, QWidget) and not isinstance(dialog, QDialog) else None))
        self._drag_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            win = self.window()
            if win:
                self._drag_pos = event.globalPosition().toPoint() - win.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            win = self.window()
            if win:
                win.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        event.accept()


class MonochromeCheckBox(QCheckBox):
    """
    Premium custom-drawn rounded squircle checkbox (16x16 indicator, 4px border-radius)
    with subpixel antialiasing and theme-adaptive colors.
    """
    def __init__(self, text: str = "", theme: str = "dark", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("background: transparent; border: none;")
        self._theme = theme

    def set_theme(self, theme: str):
        self._theme = theme
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        tokens = get_theme_tokens(self._theme)
        is_dark = (self._theme != "light")

        h = float(self.height())
        box_size = 16.0
        box_y = (h - box_size) / 2.0
        box_rect = QRectF(0.5, box_y + 0.5, box_size - 1.0, box_size - 1.0)
        
        is_checked = self.isChecked()
        is_hovered = self.underMouse()
        has_focus = self.hasFocus()

        # Focus ring for accessibility
        if has_focus:
            focus_rect = QRectF(box_rect.left() - 2, box_rect.top() - 2, box_rect.width() + 4, box_rect.height() + 4)
            focus_path = QPainterPath()
            focus_path.addRoundedRect(focus_rect, 6.0, 6.0)
            painter.setPen(QPen(QColor(tokens["border_focus"]), 1.5))
            painter.drawPath(focus_path)

        # Indicator Path (4px radius)
        path = QPainterPath()
        path.addRoundedRect(box_rect, 4.0, 4.0)

        if is_checked:
            # Checked state: background: #4E54D4 with crisp white checkmark vector
            fill_col = QColor("#4E54D4")
            chk_col = QColor("#FFFFFF")
            painter.fillPath(path, fill_col)
            
            # Draw Checkmark
            pen = QPen(chk_col, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            
            chk = QPainterPath()
            chk.moveTo(box_rect.left() + 3.5, box_rect.top() + 7.5)
            chk.lineTo(box_rect.left() + 6.2, box_rect.top() + 10.5)
            chk.lineTo(box_rect.left() + 11.5, box_rect.top() + 4.2)
            painter.drawPath(chk)
        else:
            # Unchecked state: Indicator size: 16px x 16px, border-radius: 4px, border: 1px solid #3D424A, background: #1A1B1E
            if is_dark:
                bg_col = QColor("#1A1B1E")
                border_col = QColor("#3D424A")
            else:
                bg_col = QColor(tokens["button_bg"])
                border_col = QColor(tokens["border_subtle"])
            
            painter.fillPath(path, bg_col)
            painter.setPen(QPen(border_col, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)

        # Draw Label Text: spacing: 10px; font-size: 12px; color: #EDEDED
        if self.text():
            font = QFont("Google Sans Flex", 9)
            font.setPixelSize(12)
            font.setWeight(QFont.Medium)
            font.setStyleHint(QFont.SansSerif)
            painter.setFont(font)
            text_color = QColor("#EDEDED") if is_dark else QColor(tokens["text_primary"])
            painter.setPen(text_color)
            
            text_rect = QRectF(box_size + 10.0, 0, self.width() - box_size - 10.0, h)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())

        painter.end()


class HotkeyCaptureButton(QPushButton):
    """
    Interactive keystroke-recording button matching 32px height standard
    and dynamic dark/light theme styling.
    """
    sig_hotkey_recorded = Signal(str)

    def __init__(self, initial_hotkey: str = "Ctrl+Shift+S", theme: str = "dark", parent=None):
        super().__init__(parent)
        self._hotkey = initial_hotkey or "Ctrl+Shift+S"
        self._theme = theme
        self._is_recording = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        self.setFocusPolicy(Qt.StrongFocus)
        self._update_display()
        self.clicked.connect(self._toggle_recording)

    def set_theme(self, theme: str):
        self._theme = theme
        self._update_display()

    def text(self) -> str:
        return self._hotkey

    def setText(self, val: str):
        self._hotkey = val or "Ctrl+Shift+S"
        self._update_display()

    def _update_display(self):
        tokens = get_theme_tokens(self._theme)
        is_dark = (self._theme != "light")
        bg_col = "#161719" if is_dark else tokens["surface_card"]
        border_col = "#2D3035" if is_dark else tokens["border_subtle"]
        text_col = "#EDEDED" if is_dark else tokens["text_primary"]
        hover_bg = "#26282D" if is_dark else tokens["button_hover"]
        hover_border = tokens["text_muted"]

        if self._is_recording:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tokens['surface_hover']};
                    color: {text_col};
                    border: 1px solid {tokens['border_focus']};
                    border-radius: 6px;
                    padding: 0 10px;
                    font-family: {FONT_FAMILY};
                    font-size: 12px;
                    font-weight: 600;
                    text-align: center;
                    height: 32px;
                }}
            """)
            super().setText("Press shortcut keys... (Esc to cancel)")
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_col};
                    color: {text_col};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    padding: 0 10px;
                    font-family: {FONT_FAMILY};
                    font-size: 12px;
                    font-weight: 500;
                    text-align: left;
                    height: 32px;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                    border: 1px solid {hover_border};
                    color: {text_col};
                }}
                QPushButton:focus {{
                    border: 1px solid {tokens['border_focus']};
                }}
                QPushButton:pressed {{
                    background-color: {tokens['button_pressed']};
                    border: 1px solid {tokens['border_focus']};
                    color: {text_col};
                }}
            """)
            parts = self._hotkey.split("+")
            formatted = " + ".join(f"[{p.strip()}]" for p in parts)
            super().setText(f"Shortcut:  {formatted}")

    def _toggle_recording(self):
        self._is_recording = not self._is_recording
        self._update_display()
        if self._is_recording:
            self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._is_recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key_Escape:
            self._is_recording = False
            self._update_display()
            return

        modifiers = event.modifiers()
        parts = []
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.MetaModifier:
            parts.append("Win")

        key_text = QKeySequence(key).toString()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return

        if key == Qt.Key_Print:
            key_text = "PrintScreen"

        if key_text and key_text not in parts:
            parts.append(key_text)

        if parts:
            new_combo = "+".join(parts)
            self._hotkey = new_combo
            self._is_recording = False
            self._update_display()
            self.sig_hotkey_recorded.emit(new_combo)

    def focusOutEvent(self, event):
        if self._is_recording:
            self._is_recording = False
            self._update_display()
        super().focusOutEvent(event)


class CleanComboBox(QComboBox):
    """
    QComboBox with opaque item view background, 32px height standard,
    and theme-adaptive popup view container.
    """
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedHeight(32)
        self._configure_popup()

    def set_theme(self, theme: str):
        self._theme = theme
        self._configure_popup()
        self.update()

    def _configure_popup(self):
        tokens = get_theme_tokens(self._theme)
        v = self.view()
        if v:
            w = v.window()
            if w and w != self and w != self.window():
                w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                w.setObjectName("ComboPopupWindow")
                w.setStyleSheet("QFrame#ComboPopupWindow, QWidget#ComboPopupWindow { background: transparent; border: none; }")
                w.setWindowFlags(
                    Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
                )
            v.setAutoFillBackground(False)
            v.setStyleSheet(f"QListView {{ background-color: {tokens['surface_card']}; border: 1px solid {tokens['border_subtle']}; border-radius: 8px; padding: 4px; outline: 0; }}")
            if v.viewport():
                pal = v.viewport().palette()
                pal.setColor(pal.ColorRole.Base, QColor(tokens["surface_card"]))
                pal.setColor(pal.ColorRole.Window, QColor(tokens["surface_card"]))
                v.viewport().setPalette(pal)
                v.viewport().setStyleSheet(f"background-color: {tokens['surface_card']}; border-radius: 8px;")
                v.viewport().setAutoFillBackground(True)

    def showPopup(self):
        self._configure_popup()
        super().showPopup()


class WaveThemeDelegate(QStyledItemDelegate):
    """
    Custom QComboBox item delegate rendering color swatches
    inline next to each wave theme palette name with theme-adapted styling.
    """
    def __init__(self, parent=None, theme: str = "dark"):
        super().__init__(parent)
        self._theme = theme

    def set_theme(self, theme: str):
        self._theme = theme

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        tokens = get_theme_tokens(self._theme)
        theme_name = index.data(Qt.DisplayRole)
        palette = get_wave_palette(theme_name)

        if option.state & QStyle.State_Selected or option.state & QStyle.State_MouseOver:
            item_rect = QRectF(option.rect.adjusted(2, 2, -2, -2))
            path = QPainterPath()
            path.addRoundedRect(item_rect, 6.0, 6.0)
            painter.fillPath(path, QColor(tokens["surface_hover"]))

        font = QFont("Google Sans Flex", 10, QFont.Medium)
        painter.setFont(font)
        painter.setPen(QColor(tokens["text_primary"]))
        
        swatch_r = 4.5
        swatch_spacing = 14.0
        swatch_count = len(palette)
        total_swatch_w = swatch_count * swatch_spacing
        right_start = option.rect.right() - total_swatch_w - 8.0
        center_y = float(option.rect.center().y())

        text_rect = QRectF(option.rect.left() + 10, option.rect.top(), option.rect.width() - total_swatch_w - 20.0, option.rect.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, theme_name)

        for idx, hex_code in enumerate(palette):
            cx = right_start + (idx * swatch_spacing)
            painter.setBrush(QBrush(QColor(hex_code)))
            painter.setPen(QPen(QColor(0, 0, 0, 40), 0.8))
            painter.drawEllipse(QPointF(cx, center_y), swatch_r, swatch_r)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(260, 32)


class SettingsCanvas(QFrame):
    """
    Custom frameless elevated canvas with subpixel antialiasing and theme-adaptive styling.
    """
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("SettingsCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_theme(self, theme: str):
        self._theme = theme
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        tokens = get_theme_tokens(self._theme)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        path = QPainterPath()
        path.addRoundedRect(rect, 14.0, 14.0)

        # Base canvas surface
        painter.fillPath(path, QBrush(QColor(tokens["surface_card"])))

        # 1px perimeter border
        border_pen = QPen(QColor(tokens["border_subtle"]), 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(border_pen)
        painter.drawPath(path)
        painter.end()


class SegmentedModeSelector(QWidget):
    """
    Sleek, tactile segmented toggle control [ Acrylic | Mesh ] with 32px height standard
    and dynamic dark/light theme styling.
    """
    sig_mode_changed = Signal(str)

    def __init__(self, options: list[str] = None, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.options = options or ["Acrylic", "Mesh"]
        self._theme = theme
        self._selected_index = 0
        self._hover_index = -1
        self.setFixedHeight(32)
        self.setFixedWidth(190)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)

    def set_theme(self, theme: str):
        self._theme = theme
        self.update()

    def current_mode(self) -> str:
        return self.options[self._selected_index]

    def set_mode(self, mode: str):
        mode_str = str(mode).strip()
        for idx, opt in enumerate(self.options):
            if opt.lower() == mode_str.lower():
                if self._selected_index != idx:
                    self._selected_index = idx
                    self.update()
                    self.sig_mode_changed.emit(self.options[self._selected_index])
                return
        self._selected_index = 0
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            w_seg = self.width() / max(len(self.options), 1)
            idx = int(event.position().x() // w_seg)
            idx = max(0, min(len(self.options) - 1, idx))
            if idx != self._selected_index:
                self._selected_index = idx
                self.update()
                self.sig_mode_changed.emit(self.options[self._selected_index])
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        w_seg = self.width() / max(len(self.options), 1)
        idx = int(event.position().x() // w_seg)
        idx = max(0, min(len(self.options) - 1, idx))
        if idx != self._hover_index:
            self._hover_index = idx
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Left, Qt.Key_Up):
            if self._selected_index > 0:
                self._selected_index -= 1
                self.update()
                self.sig_mode_changed.emit(self.options[self._selected_index])
            event.accept()
        elif event.key() in (Qt.Key_Right, Qt.Key_Down):
            if self._selected_index < len(self.options) - 1:
                self._selected_index += 1
                self.update()
                self.sig_mode_changed.emit(self.options[self._selected_index])
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        tokens = get_theme_tokens(self._theme)
        is_dark = (self._theme != "light")

        w = float(self.width())
        h = float(self.height())
        num = len(self.options)
        seg_w = w / float(num)

        # Base Container
        base_rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        base_path = QPainterPath()
        base_path.addRoundedRect(base_rect, 6.0, 6.0)
        painter.fillPath(base_path, QColor(tokens["button_bg"]))
        painter.setPen(QPen(QColor(tokens["border_subtle"]), 1.0))
        painter.drawPath(base_path)

        # Active Indicator Pill
        active_x = float(self._selected_index) * seg_w + 2.0
        active_rect = QRectF(active_x, 2.0, seg_w - 4.0, h - 4.0)
        active_path = QPainterPath()
        active_path.addRoundedRect(active_rect, 4.0, 4.0)
        active_fill = QColor(tokens["button_pressed"]) if is_dark else QColor("#FFFFFF")
        painter.fillPath(active_path, active_fill)
        painter.setPen(QPen(QColor(tokens["border_focus"]), 1.0))
        painter.drawPath(active_path)

        # Focus ring
        if self.hasFocus():
            painter.setPen(QPen(QColor(tokens["border_focus"]), 1.5))
            painter.drawPath(active_path)

        # Segment labels
        font = QFont("Google Sans Flex", 10, QFont.DemiBold)
        font.setStyleHint(QFont.SansSerif)
        painter.setFont(font)

        for i, opt in enumerate(self.options):
            opt_rect = QRectF(float(i) * seg_w, 0.0, seg_w, h)
            if i == self._selected_index:
                painter.setPen(QColor(tokens["text_primary"]))
            elif i == self._hover_index:
                painter.setPen(QColor(tokens["text_secondary"]))
            else:
                painter.setPen(QColor(tokens["text_muted"]))
            painter.drawText(opt_rect, Qt.AlignCenter, opt)

        painter.end()


class SettingsDialog(QDialog):
    """
    Sleek shadcn / Origin UI frameless modal dialog designed with Canvas-First Layout Rhythm,
    tight padding, crisp 1px borders, 32px height standard, and interactive ThemeToggle capsule.
    """
    sig_settings_updated = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._current_theme = self.config_manager.get("theme", "dark")
        self.setWindowTitle("MaterialSnap — Settings")
        self.resize(580, 715)

        # Frameless window configuration
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(get_settings_dialog_style(self._current_theme))

        self._drag_pos = None
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(0)

        # Frameless Elevated Canvas Frame
        self.canvas = SettingsCanvas(self._current_theme, self)
        
        # Soft elevation drop shadow effect attached to canvas
        self.shadow = QGraphicsDropShadowEffect(self.canvas)
        self.shadow.setBlurRadius(14)
        self._update_shadow_color()
        self.shadow.setOffset(0, 3)
        self.canvas.setGraphicsEffect(self.shadow)

        self.canvas_layout = QVBoxLayout(self.canvas)
        self.canvas_layout.setContentsMargins(28, 22, 28, 24)
        self.canvas_layout.setSpacing(0)

        tokens = get_theme_tokens(self._current_theme)

        # 1. Custom Titlebar with Dragging, ThemeToggle, and Close
        self.titlebar = DraggableTitleBar(self, self.canvas)
        self.titlebar.setFixedHeight(40)
        titlebar_layout = QHBoxLayout(self.titlebar)
        titlebar_layout.setContentsMargins(0, 0, 0, 0)
        titlebar_layout.setSpacing(10)

        self.icon_lbl = QLabel(self.titlebar)
        self.icon_lbl.setPixmap(IconGenerator.create_settings_icon(20, tokens["text_primary"]).pixmap(20, 20))
        titlebar_layout.addWidget(self.icon_lbl)

        self.title_lbl = QLabel("Settings & Preferences", self.titlebar)
        self.title_lbl.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 15px;
            font-weight: 700;
            color: {tokens['text_primary']};
            letter-spacing: -0.2px;
            background: transparent;
        """)
        titlebar_layout.addWidget(self.title_lbl)
        titlebar_layout.addStretch()

        # ThemeToggle Capsule Widget (64x32)
        self.theme_toggle = ThemeToggle(initial_theme=self._current_theme, parent=self.titlebar)
        self.theme_toggle.sig_theme_changed.connect(self._on_theme_toggled)
        titlebar_layout.addWidget(self.theme_toggle)

        # Close button (32x32 minimal vector close glyph)
        self.btn_close = QToolButton(self.titlebar)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setIcon(IconGenerator.create_close_icon(14, tokens["text_primary"]))
        self.btn_close.setIconSize(QSize(14, 14))
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QToolButton:hover {{
                background-color: {tokens['surface_hover']};
                border: 1px solid {tokens['border_subtle']};
            }}
            QToolButton:pressed {{
                background-color: {tokens['button_pressed']};
            }}
        """)
        self.btn_close.clicked.connect(self.reject)
        titlebar_layout.addWidget(self.btn_close)

        self.canvas_layout.addWidget(self.titlebar)
        self.canvas_layout.addSpacing(16)

        # 2. Section: GENERAL & CAPTURE
        self.sec1_header = QLabel("GENERAL & CAPTURE", self.canvas)
        self.sec1_header.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 700;
            color: {tokens['text_muted']};
            letter-spacing: 1.2px;
            background: transparent;
        """)
        self.canvas_layout.addWidget(self.sec1_header)
        self.canvas_layout.addSpacing(10)

        # Save Folder Row
        self.dir_label = QLabel("Screenshots Destination Folder", self.canvas)
        self.dir_label.setStyleSheet(f"color: {tokens['text_primary']}; font-size: 12px; font-weight: 500; font-family: {FONT_FAMILY}; background: transparent;")
        self.canvas_layout.addWidget(self.dir_label)
        self.canvas_layout.addSpacing(6)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(10)
        self.edit_dir = QLineEdit(self.canvas)
        self.edit_dir.setFixedHeight(32)
        self.btn_browse = QPushButton("Browse...", self.canvas)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFixedHeight(32)
        self.btn_browse.clicked.connect(self._on_browse_dir)
        dir_row.addWidget(self.edit_dir)
        dir_row.addWidget(self.btn_browse)
        self.canvas_layout.addLayout(dir_row)
        self.canvas_layout.addSpacing(14)

        # Global Hotkey Interactive Recorder Row
        self.hk_label = QLabel("Global Trigger Shortcut", self.canvas)
        self.hk_label.setStyleSheet(f"color: {tokens['text_primary']}; font-size: 12px; font-weight: 500; font-family: {FONT_FAMILY}; background: transparent;")
        self.canvas_layout.addWidget(self.hk_label)
        self.canvas_layout.addSpacing(6)

        self.edit_hotkey = HotkeyCaptureButton("Ctrl+Shift+S", theme=self._current_theme, parent=self.canvas)
        self.edit_hotkey.setFixedHeight(32)
        self.canvas_layout.addWidget(self.edit_hotkey)
        self.canvas_layout.addSpacing(22)

        # 3. Section: OVERLAY & WAVE SIMULATION
        self.sec2_header = QLabel("OVERLAY & WAVE SIMULATION", self.canvas)
        self.sec2_header.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 700;
            color: {tokens['text_muted']};
            letter-spacing: 1.2px;
            background: transparent;
        """)
        self.canvas_layout.addWidget(self.sec2_header)
        self.canvas_layout.addSpacing(10)

        # Wave Theme Palette Selector
        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        
        self.theme_label = QLabel("Wave Color Palette", self.canvas)
        self.theme_label.setStyleSheet(f"color: {tokens['text_primary']}; font-size: 12px; font-weight: 500; font-family: {FONT_FAMILY}; background: transparent;")
        
        self.combo_wave_theme = CleanComboBox(theme=self._current_theme, parent=self.canvas)
        self.combo_wave_theme.setCursor(Qt.PointingHandCursor)
        self.combo_wave_theme.setFixedHeight(32)
        self.combo_wave_theme.setMinimumWidth(260)
        self.wave_theme_delegate = WaveThemeDelegate(self.combo_wave_theme, theme=self._current_theme)
        self.combo_wave_theme.setItemDelegate(self.wave_theme_delegate)
        for theme_name in WAVE_THEMES.keys():
            self.combo_wave_theme.addItem(theme_name)
        self.combo_wave_theme.currentTextChanged.connect(self._on_wave_theme_changed)
        
        theme_row.addWidget(self.theme_label)
        theme_row.addStretch()
        theme_row.addWidget(self.combo_wave_theme)
        self.canvas_layout.addLayout(theme_row)
        self.canvas_layout.addSpacing(14)

        # Wave Texture Style Selector (Acrylic vs Mesh)
        style_row = QHBoxLayout()
        style_row.setSpacing(12)

        self.style_label = QLabel("Texture Style", self.canvas)
        self.style_label.setStyleSheet(f"color: {tokens['text_primary']}; font-size: 12px; font-weight: 500; font-family: {FONT_FAMILY}; background: transparent;")

        self.seg_texture_mode = SegmentedModeSelector(["Acrylic", "Mesh"], theme=self._current_theme, parent=self.canvas)
        self.seg_texture_mode.sig_mode_changed.connect(self._on_texture_mode_changed)

        style_row.addWidget(self.style_label)
        style_row.addStretch()
        style_row.addWidget(self.seg_texture_mode)
        self.canvas_layout.addLayout(style_row)
        self.canvas_layout.addSpacing(14)

        # Monochromatic Feature Checkboxes directly on canvas (16x16, 4px radius)
        self.chk_show_title = MonochromeCheckBox("Show \"MaterialSnap\" title in overlay", theme=self._current_theme, parent=self.canvas)
        self.canvas_layout.addWidget(self.chk_show_title)
        self.canvas_layout.addSpacing(6)

        self.chk_fluid_wave = MonochromeCheckBox("Enable ambient fluid wave animation", theme=self._current_theme, parent=self.canvas)
        self.canvas_layout.addWidget(self.chk_fluid_wave)
        self.canvas_layout.addSpacing(6)

        self.chk_magnifier = MonochromeCheckBox("Show precision loupe magnifier during snip", theme=self._current_theme, parent=self.canvas)
        self.canvas_layout.addWidget(self.chk_magnifier)
        self.canvas_layout.addSpacing(6)

        self.chk_auto_copy = MonochromeCheckBox("Automatically copy screenshots to clipboard", theme=self._current_theme, parent=self.canvas)
        self.canvas_layout.addWidget(self.chk_auto_copy)
        self.canvas_layout.addSpacing(6)

        self.chk_autostart = MonochromeCheckBox("Launch MaterialSnap automatically on Windows boot", theme=self._current_theme, parent=self.canvas)
        self.canvas_layout.addWidget(self.chk_autostart)

        self.canvas_layout.addStretch()

        # 4. Bottom Action Bar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel", self.canvas)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(32)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Changes", self.canvas)
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(32)
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)

        self.canvas_layout.addLayout(btn_row)

        root_layout.addWidget(self.canvas)
        if self.combo_wave_theme and self.combo_wave_theme.view() and self.combo_wave_theme.view().viewport():
            self.combo_wave_theme.view().setAutoFillBackground(False)
            self.combo_wave_theme.view().viewport().setAutoFillBackground(True)

    def _update_shadow_color(self):
        if self._current_theme == "light":
            self.shadow.setColor(QColor(0, 0, 0, 35))
        else:
            self.shadow.setColor(QColor(0, 0, 0, 180))

    def _on_theme_toggled(self, new_theme: str):
        self._current_theme = new_theme
        self.config_manager.set("theme", new_theme)
        self.set_theme(new_theme, update_toggle=False)
        self.sig_settings_updated.emit()

    def set_theme(self, theme: str, update_toggle: bool = True):
        self._current_theme = theme
        tokens = get_theme_tokens(theme)

        # 1. Update dialog stylesheet
        self.setStyleSheet(get_settings_dialog_style(theme))
        self._update_shadow_color()

        # 2. Update toggle widget if requested
        if update_toggle and hasattr(self, 'theme_toggle'):
            self.theme_toggle.set_theme(theme, animate=False)

        # 3. Canvas & Titlebar
        if hasattr(self, 'canvas'):
            self.canvas.set_theme(theme)
        if hasattr(self, 'title_lbl'):
            self.title_lbl.setStyleSheet(f"""
                font-family: {FONT_FAMILY};
                font-size: 15px;
                font-weight: 700;
                color: {tokens['text_primary']};
                letter-spacing: -0.2px;
                background: transparent;
            """)
        if hasattr(self, 'icon_lbl'):
            self.icon_lbl.setPixmap(IconGenerator.create_settings_icon(20, tokens["text_primary"]).pixmap(20, 20))
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(IconGenerator.create_close_icon(14, tokens["text_primary"]))
            self.btn_close.setStyleSheet(f"""
                QToolButton {{
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 6px;
                }}
                QToolButton:hover {{
                    background-color: {tokens['surface_hover']};
                    border: 1px solid {tokens['border_subtle']};
                }}
                QToolButton:pressed {{
                    background-color: {tokens['button_pressed']};
                }}
            """)

        # 4. Section headers & Labels
        header_qss = f"""
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 700;
            color: {tokens['text_muted']};
            letter-spacing: 1.2px;
            background: transparent;
        """
        if hasattr(self, 'sec1_header'):
            self.sec1_header.setStyleSheet(header_qss)
        if hasattr(self, 'sec2_header'):
            self.sec2_header.setStyleSheet(header_qss)

        label_qss = f"color: {tokens['text_primary']}; font-size: 12px; font-weight: 500; font-family: {FONT_FAMILY}; background: transparent;"
        for lbl_name in ('dir_label', 'hk_label', 'theme_label', 'style_label'):
            if hasattr(self, lbl_name):
                getattr(self, lbl_name).setStyleSheet(label_qss)

        # 5. Controls
        if hasattr(self, 'edit_hotkey'):
            self.edit_hotkey.set_theme(theme)
        if hasattr(self, 'combo_wave_theme'):
            self.combo_wave_theme.set_theme(theme)
        if hasattr(self, 'wave_theme_delegate'):
            self.wave_theme_delegate.set_theme(theme)
        if hasattr(self, 'seg_texture_mode'):
            self.seg_texture_mode.set_theme(theme)

        # 6. Checkboxes
        for chk_name in ('chk_show_title', 'chk_fluid_wave', 'chk_magnifier', 'chk_auto_copy', 'chk_autostart'):
            if hasattr(self, chk_name):
                getattr(self, chk_name).set_theme(theme)

        if hasattr(self, 'combo_wave_theme') and self.combo_wave_theme.view() and self.combo_wave_theme.view().viewport():
            self.combo_wave_theme.view().setAutoFillBackground(False)
            self.combo_wave_theme.view().viewport().setAutoFillBackground(True)

        self.update()

    # Window drag support
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    def _load_values(self):
        conf = self.config_manager.config
        self.edit_dir.setText(conf.get("save_directory", ""))
        self.edit_hotkey.setText(conf.get("hotkey", "Ctrl+Shift+S"))
        
        self.combo_wave_theme.blockSignals(True)
        self.combo_wave_theme.setCurrentText(conf.get("wave_theme", DEFAULT_WAVE_THEME))
        self.combo_wave_theme.blockSignals(False)

        self.seg_texture_mode.blockSignals(True)
        self.seg_texture_mode.set_mode(conf.get("wave_texture_mode", "Acrylic"))
        self.seg_texture_mode.blockSignals(False)

        self.chk_auto_copy.setChecked(conf.get("auto_copy_clipboard", True))
        self.chk_magnifier.setChecked(conf.get("show_magnifier", True))
        self.chk_show_title.setChecked(conf.get("show_title", True))
        self.chk_fluid_wave.setChecked(conf.get("enable_fluid_wave", True))
        self.chk_autostart.setChecked(is_autostart_enabled())

        active_theme = conf.get("theme", "dark")
        self.set_theme(active_theme, update_toggle=True)

    def _on_wave_theme_changed(self, theme_name: str):
        if theme_name and theme_name in WAVE_THEMES:
            self.config_manager.set("wave_theme", theme_name)
            self.sig_settings_updated.emit()

    def _on_texture_mode_changed(self, mode: str):
        if mode:
            self.config_manager.set("wave_texture_mode", mode)
            self.sig_settings_updated.emit()

    def _on_browse_dir(self):
        current = self.edit_dir.text()
        chosen = QFileDialog.getExistingDirectory(self, "Select Save Directory", current)
        if chosen:
            self.edit_dir.setText(chosen)

    def _on_save(self):
        new_dir = self.edit_dir.text().strip()
        new_hotkey = self.edit_hotkey.text().strip()
        wave_theme = self.combo_wave_theme.currentText().strip()
        texture_mode = self.seg_texture_mode.current_mode()
        auto_copy = self.chk_auto_copy.isChecked()
        magnifier = self.chk_magnifier.isChecked()
        show_title = self.chk_show_title.isChecked()
        fluid_wave = self.chk_fluid_wave.isChecked()
        autostart = self.chk_autostart.isChecked()
        theme = "dark" if self.theme_toggle.is_dark() else "light"

        if not new_dir:
            new_dir = str(Path.home() / "Pictures" / "Screenshots")

        set_autostart(autostart)

        self.config_manager.update({
            "save_directory": new_dir,
            "hotkey": new_hotkey or "Ctrl+Shift+S",
            "wave_theme": wave_theme or DEFAULT_WAVE_THEME,
            "wave_texture_mode": texture_mode,
            "auto_copy_clipboard": auto_copy,
            "show_magnifier": magnifier,
            "show_title": show_title,
            "enable_fluid_wave": fluid_wave,
            "autostart": autostart,
            "theme": theme
        })

        self.sig_settings_updated.emit()
        self.accept()
