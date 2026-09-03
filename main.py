"""TTS_Lite Desktop Application - Entry Point"""
import sys
import os

if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.ttsapp.tts-lite")

try:
    import imageio_ffmpeg
    os.environ["FFMPEG_BINARY"] = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from utils.config import Config
from utils.translations import Translations

def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    
    app = QApplication(sys.argv)
    app.setApplicationName("TTS_Lite")
    app.setOrganizationName("TTSApp")
    app.setApplicationVersion("1.0.0")
    
    config = Config()
    translations = Translations(config.language)
    
    window = MainWindow(config, translations)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
