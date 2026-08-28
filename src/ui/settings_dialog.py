from pathlib import Path
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QCheckBox, QComboBox, QFileDialog, QFrame, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush
from .styles import SETTINGS_DIALOG_STYLE, COLORS, FONT_FAMILY
from ..utils.autostart import is_autostart_enabled, set_autostart
from ..config.themes import WAVE_THEMES, DEFAULT_WAVE_THEME

class MonochromeCheckBox(QCheckBox):
    """
    Premium custom-drawn rounded squircle checkbox with monochromatic dark/white transitions.
    """
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        h = self.height()
        box_size = 18
        box_y = (h - box_size) / 2.0
        box_rect = QRectF(0, box_y, box_size, box_size)
        
        is_checked = self.isChecked()
        is_hovered = self.underMouse()

        # Indicator Path (6px squircle radius)
        path = QPainterPath()
        path.addRoundedRect(box_rect, 6, 6)

        if is_checked:
            # Checked state: Solid white fill with dark charcoal checkmark (#161719)
            painter.fillPath(path, QColor("#FFFFFF"))
            
            # Draw Checkmark
            pen = QPen(QColor("#161719"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            
            chk = QPainterPath()
            chk.moveTo(box_rect.left() + 4.5, box_rect.top() + 9.5)
            chk.lineTo(box_rect.left() + 7.5, box_rect.top() + 12.8)
            chk.lineTo(box_rect.left() + 13.5, box_rect.top() + 5.5)
            painter.drawPath(chk)
        else:
            # Unchecked state: Dark surface #2C2E33 with outline #3C4043
            bg_col = QColor("#35383E") if is_hovered else QColor("#2C2E33")
            border_col = QColor(255, 255, 255, 70) if is_hovered else QColor("#3C4043")
            
            painter.fillPath(path, bg_col)
            painter.setPen(QPen(border_col, 1.4))
            painter.drawPath(path)

        # Draw Label Text
        if self.text():
            font = QFont("Google Sans Flex", 10, QFont.Medium)
            font.setStyleHint(QFont.SansSerif)
            painter.setFont(font)
            painter.setPen(QColor("#FFFFFF"))
            
            text_rect = QRectF(box_size + 12, 0, self.width() - box_size - 12, h)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())

        painter.end()

class SettingsDialog(QDialog):
    """
    Sleek Material You / Google Search Bar styled settings modal dialog
    with strict monochromatic neutral dark-gray aesthetic.
    """
    sig_settings_updated = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("MaterialSnap — Settings")
        self.resize(540, 620)
        self.setStyleSheet(SETTINGS_DIALOG_STYLE)

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(28, 28, 28, 28)

        # Header Title
        title_label = QLabel("Settings & Preferences", self)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {FONT_FAMILY};
                font-size: 20px;
                font-weight: 800;
                color: #FFFFFF;
                background: transparent;
                letter-spacing: -0.3px;
            }}
        """)
        main_layout.addWidget(title_label)

        # Card 1: General & Capture
        card1 = QFrame(self)
        card1.setObjectName("SettingsCard")
        card1.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background-color: {COLORS['surface_card']};
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.07);
                padding: 16px;
            }}
        """)
        card1_layout = QVBoxLayout(card1)
        card1_layout.setSpacing(12)
        card1_layout.setContentsMargins(18, 18, 18, 18)

        c1_title = QLabel("General & Capture", card1)
        c1_title.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 13px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.3px;")
        card1_layout.addWidget(c1_title)

        # Save Directory Row
        dir_label = QLabel("Screenshots Save Folder:", card1)
        dir_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 500; font-family: {FONT_FAMILY};")
        card1_layout.addWidget(dir_label)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(10)
        self.edit_dir = QLineEdit(card1)
        self.btn_browse = QPushButton("Browse...", card1)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._on_browse_dir)
        dir_row.addWidget(self.edit_dir)
        dir_row.addWidget(self.btn_browse)
        card1_layout.addLayout(dir_row)

        # Global Hotkey Row
        hk_label = QLabel("Global Trigger Hotkey:", card1)
        hk_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 500; font-family: {FONT_FAMILY};")
        card1_layout.addWidget(hk_label)
        self.edit_hotkey = QLineEdit(card1)
        self.edit_hotkey.setPlaceholderText("e.g. Ctrl+Shift+S, PrintScreen, F9")
        card1_layout.addWidget(self.edit_hotkey)

        main_layout.addWidget(card1)

        # Card 2: Appearance & Overlay
        card2 = QFrame(self)
        card2.setObjectName("SettingsCard")
        card2.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background-color: {COLORS['surface_card']};
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.07);
                padding: 16px;
            }}
        """)
        card2_layout = QVBoxLayout(card2)
        card2_layout.setSpacing(10)
        card2_layout.setContentsMargins(18, 18, 18, 18)

        c2_title = QLabel("Overlay & Appearance", card2)
        c2_title.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 13px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.3px;")
        card2_layout.addWidget(c2_title)

        # Wave Theme Selector Row
        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        
        theme_label = QLabel("Wave Color Palette:", card2)
        theme_label.setStyleSheet(f"color: #FFFFFF; font-size: 13px; font-weight: 500; font-family: {FONT_FAMILY};")
        
        self.combo_wave_theme = QComboBox(card2)
        self.combo_wave_theme.setCursor(Qt.PointingHandCursor)
        for theme_name in WAVE_THEMES.keys():
            self.combo_wave_theme.addItem(theme_name)
        
        theme_row.addWidget(theme_label)
        theme_row.addStretch()
        theme_row.addWidget(self.combo_wave_theme)
        card2_layout.addLayout(theme_row)

        self.chk_show_title = MonochromeCheckBox("Show \"MaterialSnap\" title in overlay", card2)
        card2_layout.addWidget(self.chk_show_title)

        self.chk_fluid_wave = MonochromeCheckBox("Enable ambient fluid wave animation", card2)
        card2_layout.addWidget(self.chk_fluid_wave)

        self.chk_magnifier = MonochromeCheckBox("Show precision loupe magnifier during snip", card2)
        card2_layout.addWidget(self.chk_magnifier)

        self.chk_auto_copy = MonochromeCheckBox("Automatically copy screenshots to clipboard", card2)
        card2_layout.addWidget(self.chk_auto_copy)

        self.chk_autostart = MonochromeCheckBox("Launch MaterialSnap automatically on Windows boot", card2)
        card2_layout.addWidget(self.chk_autostart)

        main_layout.addWidget(card2)

        main_layout.addStretch()

        # Bottom Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Changes", self)
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(40)
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)

        main_layout.addLayout(btn_row)

    def _load_values(self):
        conf = self.config_manager.config
        self.edit_dir.setText(conf.get("save_directory", ""))
        self.edit_hotkey.setText(conf.get("hotkey", "Ctrl+Shift+S"))
        self.combo_wave_theme.setCurrentText(conf.get("wave_theme", DEFAULT_WAVE_THEME))
        self.chk_auto_copy.setChecked(conf.get("auto_copy_clipboard", True))
        self.chk_magnifier.setChecked(conf.get("show_magnifier", True))
        self.chk_show_title.setChecked(conf.get("show_title", True))
        self.chk_fluid_wave.setChecked(conf.get("enable_fluid_wave", True))
        
        # Query actual Windows registry for autostart
        self.chk_autostart.setChecked(is_autostart_enabled())

    def _on_browse_dir(self):
        current = self.edit_dir.text()
        chosen = QFileDialog.getExistingDirectory(self, "Select Save Directory", current)
        if chosen:
            self.edit_dir.setText(chosen)

    def _on_save(self):
        new_dir = self.edit_dir.text().strip()
        new_hotkey = self.edit_hotkey.text().strip()
        wave_theme = self.combo_wave_theme.currentText().strip()
        auto_copy = self.chk_auto_copy.isChecked()
        magnifier = self.chk_magnifier.isChecked()
        show_title = self.chk_show_title.isChecked()
        fluid_wave = self.chk_fluid_wave.isChecked()
        autostart = self.chk_autostart.isChecked()

        if not new_dir:
            new_dir = str(Path.home() / "Pictures" / "Screenshots")

        # Update registry autostart
        set_autostart(autostart)

        # Update config.json
        self.config_manager.update({
            "save_directory": new_dir,
            "hotkey": new_hotkey or "Ctrl+Shift+S",
            "wave_theme": wave_theme or DEFAULT_WAVE_THEME,
            "auto_copy_clipboard": auto_copy,
            "show_magnifier": magnifier,
            "show_title": show_title,
            "enable_fluid_wave": fluid_wave,
            "autostart": autostart
        })

        self.sig_settings_updated.emit()
        self.accept()
