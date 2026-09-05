"""Centralized logging configuration for TTS Lite."""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def get_log_file() -> Path:
    """Get the log file path."""
    if sys.platform == 'win32':
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / 'tts_lite'
    else:
        log_dir = Path.home() / '.cache' / 'tts_lite'
    
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / 'tts_lite.log'


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Setup application-wide logging.
    
    Args:
        debug: If True, set log level to DEBUG
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('tts_lite')
    log_level = logging.DEBUG if debug else logging.INFO
    
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with optional colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if HAS_COLORLOG:
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s',
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
    else:
        console_formatter = logging.Formatter(
            '%(levelname)-8s %(name)s: %(message)s'
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (max 5MB, keep 3 backups)
    log_file = get_log_file()
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024, 
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger


def get_logger(name: str = 'tts_lite') -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
