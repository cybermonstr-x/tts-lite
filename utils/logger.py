"""Centralized logging configuration for TTS Lite."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

try:
    import colorlog

    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def get_log_file() -> Path:
    """Get the log file path.

    Security: the log directory/file is created with owner-only
    permissions on POSIX (mode 0o700/0o600) so other users cannot
    read potentially sensitive paths. Never log full synthesis texts,
    tokens or passwords — use :func:`preview_text` from
    ``utils.security`` instead.
    """
    if sys.platform == "win32":
        import tempfile

        log_dir = Path(tempfile.gettempdir()) / "tts_lite"
    else:
        log_dir = Path.home() / ".cache" / "tts_lite" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        try:
            os.chmod(log_dir, 0o700)
        except OSError:
            pass
    log_file = log_dir / "tts_lite.log"
    if sys.platform != "win32" and log_file.exists():
        try:
            os.chmod(log_file, 0o600)
        except OSError:
            pass
    return log_file


def preview_text(text: str, max_chars: int = 10) -> str:
    """Short safe preview for logging (import-safe copy, no full user text)."""
    if not text:
        return "<empty>"
    preview = str(text)[:max_chars].replace("\n", " ").replace("\r", " ")
    return (
        f"'{preview}...' ({len(str(text))} chars)"
        if len(str(text)) > max_chars
        else f"'{preview}'"
    )


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Setup application-wide logging.

    Args:
        debug: If True, set log level to DEBUG

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("tts_lite")
    log_level = logging.DEBUG if debug else logging.INFO

    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler with optional colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if HAS_COLORLOG:
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    else:
        console_formatter = logging.Formatter("%(levelname)-8s %(name)s: %(message)s")

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with rotation (max 5MB, keep 3 backups)
    log_file = get_log_file()
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(log_level)

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")

    return logger


def get_logger(name: str = "tts_lite") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
