"""Configuration manager using QSettings for persistent storage.

Cross-platform storage (Variant V — QSettings default format):
- Windows: ``HKEY_CURRENT_USER\\Software\\TTSApp\\TTSLite`` (registry).
- Linux:   ``~/.config/TTSApp/TTSLite.conf`` (INI, automatic).
- macOS:   ``~/Library/Preferences/com.TTSApp.TTSLite.plist`` (automatic).

QSettings picks the native backend automatically, so no format-specific
code is needed. On POSIX the underlying INI file is additionally
restricted to owner-only access (chmod 600) after first sync.
"""

import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings

from utils.logger import get_logger

logger = get_logger(__name__)

ORGANIZATION = "TTSApp"
APPLICATION = "TTSLite"


class ConfigError(Exception):
    """Custom exception for configuration errors."""


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
        "export_path": "",
        "window_geometry": None,
        "engine": "auto",
        "last_engine": "edge_tts",
        "last_voice": "",
        "rate": 1.0,
        "debug_mode": False,
        # Edge TTS cloud-service consent (section 1.3 of the audit task).
        # "unknown" = not asked yet, True = accepted, False = declined.
        "edge_consent": "unknown",
    }

    VALID_THEMES = {"dark", "light"}
    VALID_LANGUAGES = {"ru", "en"}
    VALID_FORMATS = {"mp3", "wav"}
    VALID_ENGINES = {"auto", "edge_tts", "piper", "supertonic", "pyttsx3"}

    def __init__(
        self, organization: str = ORGANIZATION, application: str = APPLICATION
    ):
        try:
            # Variant V: default QSettings scope/format — native per-OS backend.
            self.settings = QSettings(organization, application)
            self._load_defaults()
            self._secure_storage()
            logger.debug("Configuration initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize configuration")
            raise ConfigError(f"Configuration initialization failed: {e}")

    def _secure_storage(self):
        """Restrict config file permissions to the current user (POSIX)."""
        if sys.platform == "win32":
            return
        try:
            self.settings.sync()
            cfg_file = self.settings.fileName()
            if cfg_file and Path(cfg_file).exists():
                Path(cfg_file).chmod(0o600)
        except Exception:
            # Best effort only — must never break startup.
            pass

    def _load_defaults(self):
        """Set default values if not present."""
        for key, value in self.DEFAULT_CONFIG.items():
            if self.settings.value(key) is None:
                self.settings.setValue(key, value)

    def config_file_path(self) -> str:
        """Return the underlying storage location (registry path or file)."""
        try:
            return str(self.settings.fileName())
        except Exception:
            return ""

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value (values are never logged for privacy)."""
        try:
            fallback = default if default is not None else self.DEFAULT_CONFIG.get(key)
            return self.settings.value(key, fallback)
        except Exception:
            logger.error("Failed to get config value")
            return default if default is not None else self.DEFAULT_CONFIG.get(key)

    def set(self, key: str, value: Any):
        """Set a configuration value (values are never logged for privacy)."""
        try:
            self.settings.setValue(key, value)
        except Exception as e:
            logger.error("Failed to set config value")
            raise ConfigError(f"Failed to set configuration {key}: {e}")

    def save(self):
        """Force save settings and re-apply secure permissions."""
        try:
            self.settings.sync()
            self._secure_storage()
            logger.debug("Configuration saved")
        except Exception as e:
            logger.error("Failed to save configuration")
            raise ConfigError("Failed to save configuration") from e

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

        if self.engine not in self.VALID_ENGINES:
            errors.append(f"Invalid engine: {self.engine}")

        if errors:
            for error in errors:
                logger.warning("Config validation: %s", error)
            return False

        logger.debug("Configuration validation passed")
        return True

    # --- Edge TTS consent helpers (audit §1.3) ---

    @property
    def edge_consent(self) -> str:
        """Edge TTS consent state: 'unknown' | True | False (stored as str/bool)."""
        raw = self.get("edge_consent", "unknown")
        if raw is True or raw == "accepted":
            return "accepted"
        if raw is False or raw == "declined":
            return "declined"
        return "unknown"

    @property
    def edge_consented(self) -> bool:
        return self.edge_consent == "accepted"

    def set_edge_consent(self, accepted: bool):
        self.set("edge_consent", "accepted" if accepted else "declined")
        self.save()

    @property
    def voice(self) -> str:
        return str(self.get("voice"))

    @voice.setter
    def voice(self, value: str):
        self.set("voice", value)

    @property
    def volume(self) -> int:
        try:
            return int(float(self.get("volume")))
        except (TypeError, ValueError):
            return int(self.DEFAULT_CONFIG["volume"])

    @volume.setter
    def volume(self, value: int):
        self.set("volume", max(0, min(100, int(float(value)))))

    @property
    def speed(self) -> float:
        try:
            return float(self.get("speed"))
        except (TypeError, ValueError):
            return float(self.DEFAULT_CONFIG["speed"])

    @speed.setter
    def speed(self, value: float):
        self.set("speed", max(0.5, min(2.0, float(value))))

    @property
    def rate(self) -> float:
        """Alias of speed (kept for README compatibility)."""
        try:
            raw = self.get("rate", None)
            if raw is None:
                return self.speed
            return max(0.5, min(2.0, float(raw)))
        except (TypeError, ValueError):
            return self.speed

    @rate.setter
    def rate(self, value: float):
        clamped = max(0.5, min(2.0, float(value)))
        self.set("rate", clamped)
        self.set("speed", clamped)

    @property
    def pitch(self) -> float:
        try:
            return float(self.get("pitch"))
        except (TypeError, ValueError):
            return float(self.DEFAULT_CONFIG["pitch"])

    @pitch.setter
    def pitch(self, value: float):
        self.set("pitch", max(0.5, min(2.0, float(value))))

    @property
    def theme(self) -> str:
        return str(self.get("theme"))

    @theme.setter
    def theme(self, value: str):
        if value not in self.VALID_THEMES:
            logger.warning("Invalid theme rejected, using default")
            value = "dark"
        self.set("theme", value)

    @property
    def language(self) -> str:
        return str(self.get("language"))

    @language.setter
    def language(self, value: str):
        if value not in self.VALID_LANGUAGES:
            logger.warning("Invalid language rejected, using default")
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
            logger.warning("Invalid export format rejected, using default")
            value = "mp3"
        self.set("export_format", value)

    @property
    def export_path(self) -> str:
        return str(self.get("export_path", ""))

    @export_path.setter
    def export_path(self, value: str):
        self.set("export_path", value)

    @property
    def engine(self) -> str:
        return str(self.get("engine"))

    @engine.setter
    def engine(self, value: str):
        if value not in self.VALID_ENGINES:
            logger.warning("Invalid engine rejected, using default")
            value = "auto"
        self.set("engine", value)

    @property
    def last_engine(self) -> str:
        return str(self.get("last_engine", self.get("engine")))

    @last_engine.setter
    def last_engine(self, value: str):
        self.set("last_engine", value)

    @property
    def last_voice(self) -> str:
        raw = self.get("last_voice", "")
        return str(raw or self.get("voice", ""))

    @last_voice.setter
    def last_voice(self, value: str):
        self.set("last_voice", value)
        self.set("voice", value)

    @property
    def debug_mode(self) -> bool:
        raw = self.get("debug_mode")
        if isinstance(raw, str):
            return raw.lower() in ("1", "true", "yes")
        return bool(raw)

    @debug_mode.setter
    def debug_mode(self, value: bool):
        self.set("debug_mode", bool(value))
