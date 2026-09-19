"""
Curated Color Hunt Theme Palettes for Ambient Fluid Mesh Wave Simulation.
"""

WAVE_THEMES = {
    "Samsung Aura": [
        "#1A102F", "#1ED8E8", "#E63BB8", "#4332D6", "#FFD768"
    ],
    "Prism Spectrum": [
        "#0B0F19", "#00F5D4", "#52FF00", "#FF003C", "#7928CA"
    ],
    "Solar Flare": [
        "#1F0B18", "#FF6B00", "#00F0B5", "#FFD000", "#8A2BE2"
    ],
    "Opal Nebula": [
        "#0D141C", "#C47AC0", "#38A3A5", "#E2E8F0", "#1B263B"
    ]
}

DEFAULT_WAVE_THEME = "Samsung Aura"

def get_wave_palette(theme_name: str) -> list[str]:
    """Returns the 5-color HEX palette for the given theme name with safe fallback to Samsung Aura."""
    if isinstance(theme_name, str) and theme_name in WAVE_THEMES:
        return list(WAVE_THEMES[theme_name])
    return list(WAVE_THEMES[DEFAULT_WAVE_THEME])

def register_wave_theme(name: str, colors: list[str]) -> bool:
    """Dynamically registers a secondary 5-color palette into the theme engine pipeline."""
    if not isinstance(name, str) or not name.strip():
        return False
    if not isinstance(colors, (list, tuple)) or len(colors) < 4:
        return False
    WAVE_THEMES[name.strip()] = list(colors)
    return True

