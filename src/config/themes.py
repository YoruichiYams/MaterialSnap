"""
Curated Color Hunt Theme Palettes for Ambient Fluid Mesh Wave Simulation.
"""

WAVE_THEMES = {
    "Twilight Mauve": ["#F8B2B2", "#AF719D", "#8B639B", "#403D88"],
    "Nordic Frost": ["#F5F5F5", "#DFF1F1", "#BBD5DA", "#FF0000"],
    "Neon Sunset": ["#E05454", "#C13383", "#792CA2", "#443199"],
    "Forest Mist": ["#E8F5E9", "#A5D6A7", "#66BB6A", "#1B5E20"],
    "Pastel Pop": ["#F599C6", "#FFEA88", "#7DCCAD", "#4D6787"],
    "Deep Ocean": ["#3368A0", "#66A3BF", "#C8DFDB", "#F2EFE7"]
}

DEFAULT_WAVE_THEME = "Twilight Mauve"

def get_wave_palette(theme_name: str) -> list[str]:
    """Returns the 4-color HEX palette for the given theme name with safe fallback to Twilight Mauve."""
    if isinstance(theme_name, str) and theme_name in WAVE_THEMES:
        return list(WAVE_THEMES[theme_name])
    return list(WAVE_THEMES[DEFAULT_WAVE_THEME])
