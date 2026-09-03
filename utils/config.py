"""Configuration manager using QSettings for persistent storage."""
import json
from pathlib import Path
from PyQt6.QtCore import QSettings

class Config:
    """Manages application settings with persistent storage."""
    
    DEFAULT_CONFIG = {
        "voice": "ru_RU-irina-medium",
        "volume": 80,
        "speed": 1.0,
        "pitch": 1.0,
        "theme": "dark",
        "language": "ru",
        "last_directory": "",
        "export_format": "mp3",
        "window_geometry": None,
    }
    
    def __init__(self):
        self.settings = QSettings("TTSApp", "TextToSpeech")
        self._load_defaults()
    
    def _load_defaults(self):
        """Set default values if not present."""
        for key, value in self.DEFAULT_CONFIG.items():
            if self.settings.value(key) is None:
                self.settings.setValue(key, value)
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return self.settings.value(key, default or self.DEFAULT_CONFIG.get(key))
    
    def set(self, key, value):
        """Set a configuration value."""
        self.settings.setValue(key, value)
    
    def save(self):
        """Force save settings."""
        self.settings.sync()
    
    @property
    def voice(self):
        return self.get("voice")
    
    @voice.setter
    def voice(self, value):
        self.set("voice", value)
    
    @property
    def volume(self):
        return int(self.get("volume"))
    
    @volume.setter
    def volume(self, value):
        self.set("volume", max(0, min(100, int(value))))
    
    @property
    def speed(self):
        return float(self.get("speed"))
    
    @speed.setter
    def speed(self, value):
        self.set("speed", max(0.5, min(2.0, float(value))))
    
    @property
    def pitch(self):
        return float(self.get("pitch"))
    
    @pitch.setter
    def pitch(self, value):
        self.set("pitch", max(0.5, min(2.0, float(value))))
    
    @property
    def theme(self):
        return self.get("theme")
    
    @theme.setter
    def theme(self, value):
        self.set("theme", value)
    
    @property
    def language(self):
        return self.get("language")
    
    @language.setter
    def language(self, value):
        self.set("language", value)
    
    @property
    def last_directory(self):
        return self.get("last_directory")
    
    @last_directory.setter
    def last_directory(self, value):
        self.set("last_directory", value)
    
    @property
    def export_format(self):
        return self.get("export_format")
    
    @export_format.setter
    def export_format(self, value):
        self.set("export_format", value)
