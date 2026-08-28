"""
Material You & Monochromatic Neutral Dark-Gray Style Tokens and QSS for MaterialSnap.
"""

FONT_FAMILY = "'Google Sans Flex', 'Google Sans', 'Segoe UI Variable Display', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"

COLORS = {
    # Neutral Dark-Gray Canvas & Surfaces
    "bg_canvas": "#161719",
    "bg_dark": "#161719",
    "surface_high": "#1E1F22",
    "surface_highest": "#282A2F",
    "surface_card": "#232529",
    "surface_input": "#1A1B1E",
    "surface_hover": "#2E3035",
    "surface_active": "#3A3D44",

    # Monochromatic Text & Accents
    "text_white": "#FFFFFF",
    "text_dark": "#161719",
    "text_primary": "#FFFFFF",
    "text_secondary": "#9AA0A6",
    "text_tertiary": "#70757A",

    # Monochromatic Action Buttons
    "btn_primary_bg": "#FFFFFF",
    "btn_primary_fg": "#161719",
    "btn_primary_hover": "#E2E3E5",
    "btn_secondary_bg": "rgba(255, 255, 255, 0.08)",
    "btn_secondary_hover": "rgba(255, 255, 255, 0.14)",

    # Toast Notifications & Context Menu
    "toast_bg": "rgba(22, 23, 25, 0.94)",
    "toast_border": "rgba(255, 255, 255, 0.10)",
    "menu_bg": "#1E1F22",
    "menu_separator": "#2A2C30",

    # Scrim & Selection Pill
    "overlay_scrim": "rgba(12, 14, 18, 0.55)",
    "pill_bg": "rgba(22, 23, 25, 0.92)",
    "pill_highlight": "#FFFFFF",
}

PILL_STYLE = f"""
QFrame#ActionPillFrame {{
    background-color: {COLORS['pill_bg']};
    border-radius: 9999px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}}

QToolButton {{
    background-color: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 9999px;
    padding: 7px 16px;
    font-family: {FONT_FAMILY};
    font-size: 13px;
    font-weight: 600;
}}

QFrame#PillDivider {{
    background-color: rgba(255, 255, 255, 0.10);
    width: 1px;
    margin: 8px 2px;
}}
"""

TOAST_STYLE = f"""
QFrame#ToastFrame {{
    background-color: {COLORS['toast_bg']};
    border-radius: 9999px;
    border: 1px solid {COLORS['toast_border']};
}}

QLabel#ToastLabel {{
    color: #FFFFFF;
    font-family: {FONT_FAMILY};
    font-size: 13px;
    font-weight: 600;
}}
"""

HEADER_TITLE_STYLE = f"""
QLabel#HeaderTitleLarge {{
    color: #FFFFFF;
    font-family: {FONT_FAMILY};
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: transparent;
}}
"""

SETTINGS_DIALOG_STYLE = f"""
QDialog {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    font-family: {FONT_FAMILY};
}}

QLineEdit {{
    background-color: {COLORS['surface_input']};
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 9999px;
    padding: 8px 16px;
    font-size: 13px;
    font-family: {FONT_FAMILY};
    selection-background-color: rgba(255, 255, 255, 0.25);
    selection-color: #FFFFFF;
}}

QLineEdit:focus {{
    border: 1px solid rgba(255, 255, 255, 0.45);
    background-color: #1E1F23;
}}

QComboBox {{
    background-color: {COLORS['surface_input']};
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
    font-family: {FONT_FAMILY};
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: rgba(255, 255, 255, 0.25);
    background-color: #1E1F23;
}}

QComboBox:focus {{
    border: 1px solid rgba(255, 255, 255, 0.45);
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: none;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #FFFFFF;
    width: 0px;
    height: 0px;
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface_card']};
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
    padding: 6px;
    selection-background-color: rgba(255, 255, 255, 0.12);
    selection-color: #FFFFFF;
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    border-radius: 8px;
    color: #FFFFFF;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: rgba(255, 255, 255, 0.08);
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: rgba(255, 255, 255, 0.14);
    color: #FFFFFF;
}}

QCheckBox {{
    color: {COLORS['text_primary']};
    font-size: 13px;
    font-weight: 500;
    spacing: 12px;
    font-family: {FONT_FAMILY};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1.5px solid #3C4043;
    background-color: #2C2E33;
}}

QCheckBox::indicator:hover {{
    border-color: rgba(255, 255, 255, 0.40);
    background-color: #35383E;
}}

QCheckBox::indicator:checked {{
    background-color: #FFFFFF;
    border-color: #FFFFFF;
}}

QPushButton {{
    background-color: {COLORS['btn_secondary_bg']};
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 9999px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    font-family: {FONT_FAMILY};
}}

QPushButton:hover {{
    background-color: {COLORS['btn_secondary_hover']};
    border-color: rgba(255, 255, 255, 0.15);
}}

QPushButton#PrimaryButton {{
    background-color: {COLORS['btn_primary_bg']};
    color: {COLORS['btn_primary_fg']};
    font-weight: 700;
    border: none;
    border-radius: 9999px;
    padding: 8px 24px;
}}

QPushButton#PrimaryButton:hover {{
    background-color: {COLORS['btn_primary_hover']};
}}
"""
