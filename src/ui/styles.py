"""
Material You, shadcn & Monochromatic Style Tokens and QSS Generators for MaterialSnap.
Supports dynamic dark and light theme switching.
"""

FONT_FAMILY = "'Google Sans Flex', 'Google Sans', 'Segoe UI Variable Display', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"

THEME_TOKENS = {
    "dark": {
        "surface_bg": "#121316",
        "surface_card": "#161719",
        "surface_hover": "#222429",
        "border_subtle": "#2D3035",
        "border_focus": "#4E54D4",
        "text_primary": "#EDEDED",
        "text_secondary": "#8A8F98",
        "text_muted": "#636873",
        "button_bg": "#1A1B1E",
        "button_hover": "#26282D",
        "button_pressed": "#2F333A",
        "shadow_color": "rgba(0, 0, 0, 0.45)",
        "scrim_overlay": "rgba(15, 12, 28, 140)",
    },
    "light": {
        "surface_bg": "#FBFBFB",
        "surface_card": "#FFFFFF",
        "surface_hover": "#F4F4F5",
        "border_subtle": "#E4E4E7",
        "border_focus": "#4E54D4",
        "text_primary": "#18181B",
        "text_secondary": "#52525B",
        "text_muted": "#71717A",
        "button_bg": "#F4F4F5",
        "button_hover": "#E4E4E7",
        "button_pressed": "#D4D4D8",
        "shadow_color": "rgba(0, 0, 0, 0.08)",
        "scrim_overlay": "rgba(255, 255, 255, 160)",
    }
}

def get_theme_tokens(theme: str = "dark") -> dict:
    """Returns the design tokens for the requested theme, defaulting to dark."""
    theme_key = "light" if theme == "light" else "dark"
    return THEME_TOKENS[theme_key]

# Legacy color dictionary backwards-compatibility
COLORS = {
    # Neutral Dark-Gray Canvas & Surfaces
    "bg_canvas": "#161719",
    "bg_dark": "#161719",
    "surface_high": "#1E1F22",
    "surface_highest": "#282A2F",
    "surface_card": "#232529",
    "surface_modal": "#161719",
    "surface_input": "#1A1B1E",
    "surface_hover": "#2E3035",
    "surface_active": "#3A3D44",
    "border_glass": "#2A2D32",
    "border_solid": "#2A2D32",
    "border_hover": "#3D424A",
    "border_focus": "#454B54",
    "border_divider": "#26292E",

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
    "btn_secondary_bg": "#26292E",
    "btn_secondary_hover": "#35383E",

    # Toast Notifications & Context Menu
    "toast_bg": "rgba(22, 23, 25, 0.94)",
    "toast_border": "#2A2D32",
    "menu_bg": "#161719",
    "menu_separator": "#26292E",

    # Scrim & Selection Pill
    "overlay_scrim": "rgba(12, 14, 18, 0.55)",
    "pill_bg": "rgba(22, 23, 25, 0.92)",
    "pill_highlight": "#FFFFFF",
}

def get_menu_style(theme: str = "dark") -> str:
    tokens = get_theme_tokens(theme)
    is_dark = (theme != "light")
    bg_color = "#161719" if is_dark else tokens['surface_card']
    border_color = "#2D3035" if is_dark else tokens['border_subtle']
    text_color = "#EDEDED" if is_dark else tokens['text_primary']
    hover_bg = "#26282D" if is_dark else tokens['surface_hover']
    hover_text = "#FFFFFF" if is_dark else tokens['text_primary']
    sep_color = "#2D3035" if is_dark else tokens['border_subtle']

    return f"""
QMenu {{
    background-color: {bg_color};
    border: 1px solid {border_color};
    border-radius: 10px;
    padding: 6px;
    font-family: {FONT_FAMILY};
}}

QMenu::item {{
    height: 32px;
    padding: 4px 14px 4px 36px;
    border-radius: 6px;
    color: {text_color};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
    font-family: {FONT_FAMILY};
}}

QMenu::item:selected {{
    background-color: {hover_bg};
    color: {hover_text};
}}

QMenu::icon {{
    position: absolute;
    left: 10px;
    width: 16px;
    height: 16px;
}}

QMenu::indicator {{
    position: absolute;
    left: 10px;
    width: 16px;
    height: 16px;
}}

QMenu::separator {{
    height: 1px;
    background: {sep_color};
    margin: 4px 6px;
}}
"""

def get_pill_style(theme: str = "dark") -> str:
    tokens = get_theme_tokens(theme)
    return f"""
QFrame#ActionPillFrame {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
}}

QToolButton#ActionPillButton, QToolButton.ActionPillButton {{
    background-color: {tokens['surface_card']};
    color: {tokens['text_primary']};
    padding: 6px 14px;
    height: 32px;
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: 500;
    text-align: center;
}}

QToolButton#ActionPillButton[position="first"] {{
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
    border: 1px solid {tokens['border_subtle']};
}}

QToolButton#ActionPillButton[position="middle"] {{
    border-radius: 0px;
    border-top: 1px solid {tokens['border_subtle']};
    border-bottom: 1px solid {tokens['border_subtle']};
    border-right: 1px solid {tokens['border_subtle']};
    border-left: none;
}}

QToolButton#ActionPillButton[position="last"] {{
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    border-top: 1px solid {tokens['border_subtle']};
    border-bottom: 1px solid {tokens['border_subtle']};
    border-right: 1px solid {tokens['border_subtle']};
    border-left: none;
}}

QToolButton#ActionPillButton:hover, QToolButton.ActionPillButton:hover {{
    background-color: {tokens['surface_hover']};
    color: {tokens['text_primary']};
}}

QToolButton#ActionPillButton:pressed, QToolButton.ActionPillButton:pressed {{
    background-color: {tokens['button_pressed']};
    color: {tokens['text_primary']};
}}
"""

def get_toast_style(theme: str = "dark") -> str:
    tokens = get_theme_tokens(theme)
    return f"""
QFrame#ToastFrame {{
    background-color: transparent;
    border-radius: 10px;
    border: none;
}}

QLabel#ToastLabel {{
    color: {tokens['text_primary']};
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: 500;
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

def get_settings_dialog_style(theme: str = "dark") -> str:
    tokens = get_theme_tokens(theme)
    is_dark = (theme != "light")

    input_bg = "#161719" if is_dark else "#FFFFFF"
    input_fg = "#EDEDED" if is_dark else tokens['text_primary']
    input_border = "#2D3035" if is_dark else tokens['border_subtle']

    btn_bg = "#1E1F22" if is_dark else tokens['button_bg']
    btn_fg = "#EDEDED" if is_dark else tokens['text_primary']
    btn_border = "#2D3035" if is_dark else tokens['border_subtle']
    btn_hover_bg = "#26282D" if is_dark else tokens['button_hover']
    btn_hover_fg = "#FFFFFF" if is_dark else tokens['text_primary']

    primary_bg = "#EDEDED" if is_dark else "#18181B"
    primary_fg = "#121316" if is_dark else "#FFFFFF"
    primary_hover_bg = "#FFFFFF" if is_dark else "#27272A"
    primary_pressed_bg = "#D4D4D8" if is_dark else "#3F3F46"
    arrow_color = tokens['text_secondary']

    return f"""
QDialog {{
    background: transparent;
    color: {tokens['text_primary']};
    font-family: {FONT_FAMILY};
}}

QLineEdit {{
    background-color: {input_bg};
    color: {input_fg};
    border: 1px solid {input_border};
    border-radius: 6px;
    padding: 0 10px;
    height: 32px;
    font-size: 12px;
    font-family: {FONT_FAMILY};
    selection-background-color: rgba(78, 84, 212, 0.35);
    selection-color: {input_fg};
}}

QLineEdit:hover {{
    border: 1px solid {tokens['text_muted']};
}}

QLineEdit:focus {{
    border: 1px solid {tokens['border_focus']};
}}

QComboBox {{
    background-color: {input_bg};
    color: {input_fg};
    border: 1px solid {input_border};
    border-radius: 6px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 500;
    font-family: {FONT_FAMILY};
    height: 32px;
}}

QComboBox:hover {{
    border: 1px solid {tokens['text_muted']};
    background-color: {tokens['surface_hover']};
}}

QComboBox:focus, QComboBox:on {{
    border: 1px solid {tokens['border_focus']};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {arrow_color};
    width: 0px;
    height: 0px;
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {tokens['surface_card']};
    background: {tokens['surface_card']};
    border: 1px solid {tokens['border_subtle']};
    border-radius: 8px;
    padding: 4px;
    outline: 0;
    selection-background-color: {tokens['surface_hover']};
}}

QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 4px 10px;
    border-radius: 4px;
    color: {tokens['text_primary']};
    background-color: transparent;
}}

QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {{
    background-color: {tokens['surface_hover']};
    color: {tokens['text_primary']};
}}

QPushButton {{
    background-color: {btn_bg};
    color: {btn_fg};
    border: 1px solid {btn_border};
    border-radius: 6px;
    padding: 0 14px;
    height: 32px;
    font-size: 12px;
    font-weight: 500;
    font-family: {FONT_FAMILY};
}}

QPushButton:hover {{
    background-color: {btn_hover_bg};
    border: 1px solid {btn_border};
    color: {btn_hover_fg};
}}

QPushButton:focus {{
    border: 1px solid {tokens['border_focus']};
}}

QPushButton:pressed {{
    background-color: {tokens['button_pressed']};
    border: 1px solid {tokens['border_focus']};
    color: {btn_fg};
}}

QPushButton#PrimaryButton {{
    background-color: {primary_bg};
    color: {primary_fg};
    font-weight: 600;
    border: 1px solid {btn_border};
    border-radius: 6px;
    height: 32px;
    padding: 0 16px;
    font-size: 12px;
    font-family: {FONT_FAMILY};
}}

QPushButton#PrimaryButton:hover {{
    background-color: {primary_hover_bg};
    border: 1px solid {btn_border};
    color: {primary_fg};
}}

QPushButton#PrimaryButton:focus {{
    border: 1px solid {tokens['border_focus']};
}}

QPushButton#PrimaryButton:pressed {{
    background-color: {primary_pressed_bg};
    border: 1px solid {btn_border};
    color: {primary_fg};
}}
"""

def get_application_stylesheet(theme: str = "dark") -> str:
    """Generates the unified global stylesheet across the application for the given theme."""
    return f"""
{get_menu_style(theme)}
{get_pill_style(theme)}
{get_toast_style(theme)}
{HEADER_TITLE_STYLE}
{get_settings_dialog_style(theme)}
"""

# Static default theme constants for backwards compatibility
MENU_STYLE = get_menu_style("dark")
PILL_STYLE = get_pill_style("dark")
TOAST_STYLE = get_toast_style("dark")
SETTINGS_DIALOG_STYLE = get_settings_dialog_style("dark")
GLOBAL_STYLE = get_application_stylesheet("dark")
