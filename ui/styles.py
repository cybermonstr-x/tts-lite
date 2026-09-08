"""QSS style loading and management."""

from pathlib import Path

from PySide6.QtWidgets import QApplication

# Style directory
STYLES_DIR = Path(__file__).parent.parent / "resources" / "styles"


def load_stylesheet(theme: str = "dark") -> str:
    """Load QSS stylesheet for the specified theme."""
    from utils.logger import get_logger

    style_file = STYLES_DIR / f"{theme}.qss"

    if not style_file.exists():
        get_logger(__name__).warning("Style file not found: %s", style_file)
        return ""

    with open(style_file, "r", encoding="utf-8") as f:
        return f.read()


def apply_theme(app: QApplication, theme: str = "dark"):
    """Apply theme to the application."""
    stylesheet = load_stylesheet(theme)
    app.setStyleSheet(stylesheet)
