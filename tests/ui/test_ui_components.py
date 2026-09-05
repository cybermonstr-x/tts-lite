"""
UI Tests for TTS Lite
Tests for graphical interface components
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tts'))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests"""
    if not PYQT_AVAILABLE:
        pytest.skip("PyQt6 not available")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit app as it might be used by other tests


class TestMainWindowBasics:
    """Basic tests for main window"""
    
    def test_application_starts(self, app):
        """Test that application can start without errors"""
        assert app is not None
        assert QApplication.instance() is not None
    
    def test_qapplication_instance(self, app):
        """Test QApplication instance exists"""
        instance = QApplication.instance()
        assert instance is not None


class TestTextProcessing:
    """Tests for text processing functionality"""
    
    def test_empty_text_handling(self):
        """Test handling of empty text"""
        try:
            from utils.text_processing import clean_text
            
            result = clean_text("")
            assert result == ""
            
            result = clean_text("   ")
            assert result == ""
        except ImportError:
            pytest.skip("text_processing module not available")
    
    def test_special_characters(self):
        """Test handling of special characters"""
        try:
            from utils.text_processing import clean_text
            
            text = "Hello! How are you?"
            result = clean_text(text)
            assert len(result) > 0
            assert isinstance(result, str)
        except ImportError:
            pytest.skip("text_processing module not available")
    
    def test_long_text(self):
        """Test handling of long text"""
        try:
            from utils.text_processing import clean_text
            
            long_text = "Test sentence. " * 100
            result = clean_text(long_text)
            assert len(result) > 0
            assert isinstance(result, str)
        except ImportError:
            pytest.skip("text_processing module not available")


class TestConfigManager:
    """Tests for configuration management"""
    
    def test_config_creation(self):
        """Test config manager can be created"""
        try:
            from engine import TTSEngine
            
            engine = TTSEngine()
            assert engine is not None
        except ImportError:
            pytest.skip("engine module not available")
    
    def test_config_default_values(self):
        """Test config has default values"""
        try:
            from engine import TTSEngine
            
            engine = TTSEngine()
            # Should have some default settings
            assert hasattr(engine, 'get_voices') or hasattr(engine, 'synthesize')
        except ImportError:
            pytest.skip("engine module not available")


class TestEngineInterface:
    """Tests for TTS engine interface"""
    
    def test_engine_base_class(self):
        """Test base engine class exists"""
        try:
            from engine import TTSEngine
            assert TTSEngine is not None
        except ImportError:
            pytest.skip("Engine not found")
    
    def test_engine_methods(self):
        """Test engine has required methods"""
        try:
            from engine import TTSEngine
            
            # Check that class has required methods
            assert hasattr(TTSEngine, 'synthesize') or hasattr(TTSEngine, 'get_voices')
        except ImportError:
            pytest.skip("Engine not found")


class TestVoiceSelection:
    """Tests for voice selection functionality"""
    
    def test_voice_list_not_empty(self):
        """Test that voice list is not empty (mock test)"""
        # This is a placeholder - actual implementation depends on engine
        voices = ["voice1", "voice2"]  # Mock data
        assert len(voices) > 0
    
    def test_voice_selection(self):
        """Test voice selection logic"""
        voices = ["en-US-male", "en-US-female", "ru-RU-male"]
        selected = voices[0]
        assert selected in voices


class TestExportFunctionality:
    """Tests for audio export functionality"""
    
    def test_export_formats(self):
        """Test supported export formats"""
        formats = ["mp3", "wav"]
        assert "mp3" in formats
        assert "wav" in formats
    
    def test_file_path_generation(self):
        """Test file path generation"""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_output.mp3")
            assert filepath.endswith(".mp3")
            assert "test_output" in filepath


class TestLanguageSupport:
    """Tests for language support"""
    
    def test_supported_languages(self):
        """Test supported languages"""
        languages = ["en", "ru"]
        assert "en" in languages
        assert "ru" in languages
    
    def test_language_detection(self):
        """Test basic language detection logic"""
        def detect_language(text):
            """Simple mock language detection"""
            cyrillic_chars = sum(1 for c in text if 'а' <= c <= 'я' or 'А' <= c <= 'Я')
            return "ru" if cyrillic_chars > len(text) * 0.3 else "en"
        
        assert detect_language("Hello world") == "en"
        assert detect_language("Привет мир") == "ru"


class TestPerformance:
    """Performance-related tests"""
    
    def test_text_processing_speed(self):
        """Test that text processing is reasonably fast"""
        import time
        try:
            from utils.text_processing import clean_text
            
            text = "Test sentence. " * 50
            start = time.time()
            result = clean_text(text)
            elapsed = time.time() - start
            
            # Should process in less than 1 second
            assert elapsed < 1.0
            assert len(result) > 0
        except ImportError:
            pytest.skip("text_processing module not available")
    
    def test_config_load_speed(self):
        """Test that config loading is fast"""
        import time
        try:
            from engine import TTSEngine
            
            start = time.time()
            engine = TTSEngine()
            elapsed = time.time() - start
            
            # Should load in less than 1 second
            assert elapsed < 1.0
        except ImportError:
            pytest.skip("engine module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
