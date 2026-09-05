"""Configuration manager using QSettings for persistent storage."""
import json
import sys
from pathlib import Path
from typing import Any, Optional
from PySide6.QtCore import QSettings

from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


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
        "engine": "auto",
        "debug_mode": False,
    }
    
    VALID_THEMES = {"dark", "light"}
    VALID_LANGUAGES = {"ru", "en"}
    VALID_FORMATS = {"mp3", "wav"}
    
    def __init__(self, organization: str = "TTSApp", application: str = "TextToSpeech"):
        try:
            self.settings = QSettings(organization, application)
            self._load_defaults()
            logger.debug("Configuration initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            raise ConfigError(f"Configuration initialization failed: {e}")
    
    def _load_defaults(self):
        """Set default values if not present."""
        for key, value in self.DEFAULT_CONFIG.items():
            if self.settings.value(key) is None:
                self.settings.setValue(key, value)
                logger.debug(f"Set default config: {key}={value}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        try:
            value = self.settings.value(key, default or self.DEFAULT_CONFIG.get(key))
            logger.debug(f"Config get: {key}={value}")
            return value
        except Exception as e:
            logger.error(f"Failed to get config {key}: {e}")
            return default or self.DEFAULT_CONFIG.get(key)
    
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        try:
            self.settings.setValue(key, value)
            logger.debug(f"Config set: {key}={value}")
        except Exception as e:
            logger.error(f"Failed to set config {key}: {e}")
            raise ConfigError(f"Failed to set configuration {key}: {e}")
    
    def save(self):
        """Force save settings."""
        try:
            self.settings.sync()
            logger.debug("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigError("Failed to save configuration")
    
    def validate(self) -> bool:
        """Validate current configuration values."""
        errors = []
        
        if self.theme not in self.VALID_THEMES:
            errors.append(f"Invalid theme: {self.theme}")
        
        if self.language not in self.VALID_LANGUAGES:
            errors.append(f"Invalid language: {self.language}")
        
        if self.export_format not in self.VALID_FORMATS:
            errors.append(f"Invalid export format: {self.export_format}")
        
        if not (0 <= self.volume <= 100):
            errors.append(f"Volume out of range: {self.volume}")
        
        if not (0.5 <= self.speed <= 2.0):
            errors.append(f"Speed out of range: {self.speed}")
        
        if not (0.5 <= self.pitch <= 2.0):
            errors.append(f"Pitch out of range: {self.pitch}")
        
        if errors:
            for error in errors:
                logger.warning(f"Config validation: {error}")
            return False
        
        logger.debug("Configuration validation passed")
        return True
    
    @property
    def voice(self) -> str:
        return str(self.get("voice"))
    
    @voice.setter
    def voice(self, value: str):
        self.set("voice", value)
    
    @property
    def volume(self) -> int:
        return int(self.get("volume"))
    
    @volume.setter
    def volume(self, value: int):
        self.set("volume", max(0, min(100, int(value))))
    
    @property
    def speed(self) -> float:
        return float(self.get("speed"))
    
    @speed.setter
    def speed(self, value: float):
        self.set("speed", max(0.5, min(2.0, float(value))))
    
    @property
    def pitch(self) -> float:
        return float(self.get("pitch"))
    
    @pitch.setter
    def pitch(self, value: float):
        self.set("pitch", max(0.5, min(2.0, float(value))))
    
    @property
    def theme(self) -> str:
        return str(self.get("theme"))
    
    @theme.setter
    def theme(self, value: str):
        if value not in self.VALID_THEMES:
            logger.warning(f"Invalid theme '{value}', using default")
            value = "dark"
        self.set("theme", value)
    
    @property
    def language(self) -> str:
        return str(self.get("language"))
    
    @language.setter
    def language(self, value: str):
        if value not in self.VALID_LANGUAGES:
            logger.warning(f"Invalid language '{value}', using default")
            value = "ru"
        self.set("language", value)
    
    @property
    def last_directory(self) -> str:
        return str(self.get("last_directory"))
    
    @last_directory.setter
    def last_directory(self, value: str):
        self.set("last_directory", value)
    
    @property
    def export_format(self) -> str:
        return str(self.get("export_format"))
    
    @export_format.setter
    def export_format(self, value: str):
        if value not in self.VALID_FORMATS:
            logger.warning(f"Invalid export format '{value}', using default")
            value = "mp3"
        self.set("export_format", value)
    
    @property
    def engine(self) -> str:
        return str(self.get("engine"))
    
    @engine.setter
    def engine(self, value: str):
        self.set("engine", value)
    
    @property
    def debug_mode(self) -> bool:
        return bool(self.get("debug_mode"))
    
    @debug_mode.setter
    def debug_mode(self, value: bool):
        self.set("debug_mode", value)
