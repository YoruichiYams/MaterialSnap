import sys
import os
import json
from pathlib import Path
from .themes import WAVE_THEMES, DEFAULT_WAVE_THEME

DEFAULT_CONFIG = {
    "save_directory": str(Path.home() / "Pictures" / "Screenshots"),
    "auto_copy_clipboard": True,
    "hotkey": "Ctrl+Shift+S",
    "autostart": False,
    "sound_feedback": True,
    "show_magnifier": True,
    "show_title": True,
    "enable_fluid_wave": True,
    "wave_theme": DEFAULT_WAVE_THEME,
    "save_format": "PNG",
    "theme": "dark"
}

class ConfigManager:
    """Manages application settings stored in a local config.json file."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # If running as a frozen executable, save beside the executable
            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).resolve().parent
            else:
                base_dir = Path(__file__).resolve().parent.parent.parent
            self.config_path = base_dir / "config.json"
        else:
            self.config_path = Path(config_path)
            
        self._config = dict(DEFAULT_CONFIG)
        self.load()
        
    def load(self) -> dict:
        """Load configuration from disk, creating default if not found."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config.update(data)
            except Exception as e:
                print(f"[ConfigManager] Error reading config file: {e}")
                self.save()
        else:
            self.save()
            
        # Validate wave_theme
        if self._config.get("wave_theme") not in WAVE_THEMES:
            self._config["wave_theme"] = DEFAULT_WAVE_THEME

        # Ensure screenshot directory exists and is writable
        try:
            from ..utils.path_security import validate_save_directory
            validated_dir = validate_save_directory(self._config.get("save_directory", DEFAULT_CONFIG["save_directory"]))
            self._config["save_directory"] = str(validated_dir)
        except Exception:
            pass
            
        return self._config

    def save(self):
        """Save current configuration to disk."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error saving config file: {e}")

    def get(self, key: str, default=None):
        val = self._config.get(key, default)
        if key == "wave_theme" and val not in WAVE_THEMES:
            return DEFAULT_WAVE_THEME
        return val

    def set(self, key: str, value):
        self._config[key] = value
        self.save()

    def update(self, new_data: dict):
        self._config.update(new_data)
        self.save()

    @property
    def config(self) -> dict:
        return dict(self._config)
