"""Tests for configuration manager."""
import pytest
from unittest.mock import Mock, patch
from utils.config import Config


@pytest.fixture
def mock_qsettings():
    """Fixture to mock QSettings."""
    with patch('utils.config.QSettings') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        # Setup default behavior
        mock_instance.value.return_value = None
        yield mock_instance


class TestConfigDefaults:
    """Tests for Config default values."""
    
    def test_default_config_keys(self):
        """Test that DEFAULT_CONFIG has expected keys."""
        expected_keys = {
            "voice", "volume", "speed", "pitch",
            "theme", "language", "last_directory",
            "export_format", "window_geometry"
        }
        assert set(Config.DEFAULT_CONFIG.keys()) == expected_keys
    
    def test_default_volume_range(self):
        """Test that default volume is in valid range."""
        assert 0 <= Config.DEFAULT_CONFIG["volume"] <= 100
    
    def test_default_speed_range(self):
        """Test that default speed is in valid range."""
        assert 0.5 <= Config.DEFAULT_CONFIG["speed"] <= 2.0
    
    def test_default_pitch_range(self):
        """Test that default pitch is in valid range."""
        assert 0.5 <= Config.DEFAULT_CONFIG["pitch"] <= 2.0
    
    def test_default_theme(self):
        """Test that default theme is valid."""
        assert Config.DEFAULT_CONFIG["theme"] in ["dark", "light"]
    
    def test_default_language(self):
        """Test that default language is valid."""
        assert Config.DEFAULT_CONFIG["language"] in ["ru", "en"]
    
    def test_default_export_format(self):
        """Test that default export format is valid."""
        assert Config.DEFAULT_CONFIG["export_format"] in ["mp3", "wav"]


class TestConfigGetSet:
    """Tests for Config get/set methods."""
    
    def test_get_default_value(self, mock_qsettings):
        """Test getting a value returns default when not set."""
        # When settings.value returns None, the get method should use DEFAULT_CONFIG
        def value_side_effect(key, default=None):
            if default is not None:
                return default
            return None
        
        mock_qsettings.value.side_effect = value_side_effect
        config = Config()
        
        result = config.get("voice")
        
        assert result == Config.DEFAULT_CONFIG["voice"]
    
    def test_get_custom_value(self, mock_qsettings):
        """Test getting a custom value."""
        mock_qsettings.value.return_value = "custom_voice"
        config = Config()
        
        result = config.get("voice")
        
        assert result == "custom_voice"
    
    def test_get_with_fallback_default(self, mock_qsettings):
        """Test get with fallback default parameter."""
        # When a default is provided and settings.value returns None,
        # the provided default should be used
        def value_side_effect(key, default=None):
            return default  # Return the default provided by get()
        
        mock_qsettings.value.side_effect = value_side_effect
        config = Config()
        
        result = config.get("unknown_key", "fallback")
        
        assert result == "fallback"
    
    def test_set_value(self, mock_qsettings):
        """Test setting a value."""
        mock_qsettings.value.return_value = None
        config = Config()
        
        # Reset the call count after initialization
        mock_qsettings.setValue.reset_mock()
        config.set("test_key", "test_value")
        
        mock_qsettings.setValue.assert_called_once_with("test_key", "test_value")
    
    def test_save_calls_sync(self, mock_qsettings):
        """Test that save() calls sync()."""
        config = Config()
        
        config.save()
        
        mock_qsettings.sync.assert_called_once()


class TestConfigProperties:
    """Tests for Config property getters/setters."""
    
    def test_voice_property_get(self, mock_qsettings):
        """Test voice property getter."""
        config = Config()
        mock_qsettings.value.return_value = "test_voice"
        
        assert config.voice == "test_voice"
    
    def test_voice_property_set(self, mock_qsettings):
        """Test voice property setter."""
        config = Config()
        
        config.voice = "new_voice"
        
        mock_qsettings.setValue.assert_called_with("voice", "new_voice")
    
    def test_volume_property_clamps_max(self, mock_qsettings):
        """Test volume property clamps to max 100."""
        config = Config()
        
        config.volume = 150
        
        mock_qsettings.setValue.assert_called_with("volume", 100)
    
    def test_volume_property_clamps_min(self, mock_qsettings):
        """Test volume property clamps to min 0."""
        config = Config()
        
        config.volume = -10
        
        mock_qsettings.setValue.assert_called_with("volume", 0)
    
    def test_volume_property_valid_range(self, mock_qsettings):
        """Test volume property with valid value."""
        config = Config()
        
        config.volume = 75
        
        mock_qsettings.setValue.assert_called_with("volume", 75)
    
    def test_speed_property_clamps_max(self, mock_qsettings):
        """Test speed property clamps to max 2.0."""
        config = Config()
        
        config.speed = 5.0
        
        mock_qsettings.setValue.assert_called_with("speed", 2.0)
    
    def test_speed_property_clamps_min(self, mock_qsettings):
        """Test speed property clamps to min 0.5."""
        config = Config()
        
        config.speed = 0.1
        
        mock_qsettings.setValue.assert_called_with("speed", 0.5)
    
    def test_pitch_property_clamps_max(self, mock_qsettings):
        """Test pitch property clamps to max 2.0."""
        config = Config()
        
        config.pitch = 3.0
        
        mock_qsettings.setValue.assert_called_with("pitch", 2.0)
    
    def test_pitch_property_clamps_min(self, mock_qsettings):
        """Test pitch property clamps to min 0.5."""
        config = Config()
        
        config.pitch = 0.2
        
        mock_qsettings.setValue.assert_called_with("pitch", 0.5)
    
    def test_theme_property(self, mock_qsettings):
        """Test theme property."""
        config = Config()
        mock_qsettings.value.return_value = "light"
        
        assert config.theme == "light"
        
        config.theme = "dark"
        mock_qsettings.setValue.assert_called_with("theme", "dark")
    
    def test_language_property(self, mock_qsettings):
        """Test language property."""
        config = Config()
        mock_qsettings.value.return_value = "en"
        
        assert config.language == "en"
        
        config.language = "ru"
        mock_qsettings.setValue.assert_called_with("language", "ru")
    
    def test_last_directory_property(self, mock_qsettings):
        """Test last_directory property."""
        config = Config()
        mock_qsettings.value.return_value = "/path/to/dir"
        
        assert config.last_directory == "/path/to/dir"
    
    def test_export_format_property(self, mock_qsettings):
        """Test export_format property."""
        config = Config()
        mock_qsettings.value.return_value = "wav"
        
        assert config.export_format == "wav"
        
        config.export_format = "mp3"
        mock_qsettings.setValue.assert_called_with("export_format", "mp3")


class TestConfigInitialization:
    """Tests for Config initialization."""
    
    def test_init_loads_defaults(self, mock_qsettings):
        """Test that __init__ loads defaults for missing values."""
        mock_qsettings.value.return_value = None
        
        config = Config()
        
        # Should call setValue for each default key
        assert mock_qsettings.setValue.call_count >= len(Config.DEFAULT_CONFIG)
    
    def test_init_doesnt_overwrite_existing(self, mock_qsettings):
        """Test that __init__ doesn't overwrite existing values."""
        mock_qsettings.value.return_value = "existing_value"
        
        config = Config()
        
        # Should not call setValue if value exists
        mock_qsettings.setValue.assert_not_called()
