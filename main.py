"""TTS_Lite Desktop Application - Entry Point"""
import sys
import os

# Setup logging before any other imports
from utils.logger import setup_logging, get_logger

def main():
    # Initialize logging
    debug_mode = os.environ.get("TTS_LITE_DEBUG", "0") == "1"
    logger = setup_logging(debug=debug_mode)
    logger.info("Starting TTS Lite application")
    
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.ttsapp.tts-lite")
            logger.debug("Set Windows AppUserModelID")
        
        try:
            import imageio_ffmpeg
            os.environ["FFMPEG_BINARY"] = imageio_ffmpeg.get_ffmpeg_exe()
            logger.debug(f"FFmpeg path: {imageio_ffmpeg.get_ffmpeg_exe()}")
        except ImportError:
            logger.warning("imageio_ffmpeg not found, using system ffmpeg")
        
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from ui.main_window import MainWindow
        from utils.config import Config, ConfigError
        from utils.translations import Translations
        
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        
        app = QApplication(sys.argv)
        app.setApplicationName("TTS_Lite")
        app.setOrganizationName("TTSApp")
        app.setApplicationVersion("1.0.3")
        
        # Initialize configuration
        try:
            config = Config()
            if not config.validate():
                logger.warning("Configuration validation failed, using defaults")
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
            # Fallback to default config
            config = Config()
        
        translations = Translations(config.language)
        logger.info(f"Language set to: {config.language}")
        
        window = MainWindow(config, translations)
        window.show()
        
        logger.info("Application started successfully")
        
        exit_code = app.exec()
        logger.info(f"Application exiting with code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        # Show error message to user (never create a second QApplication).
        try:
            from PySide6.QtWidgets import QMessageBox, QApplication
            app = QApplication.instance()
            if app is not None:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("TTS Lite - Fatal Error")
                msg_box.setText(f"A fatal error occurred: {e}")
                msg_box.setDetailedText("Check the log file for more details.")
                msg_box.exec()
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
