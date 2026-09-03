"""QSS style loading and management."""
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Style directory
STYLES_DIR = Path(__file__).parent.parent / "resources" / "styles"

def load_stylesheet(theme: str = "dark") -> str:
    """Load QSS stylesheet for the specified theme."""
    style_file = STYLES_DIR / f"{theme}.qss"
    
    if not style_file.exists():
        print(f"Style file not found: {style_file}")
        return ""
    
    with open(style_file, 'r', encoding='utf-8') as f:
        return f.read()

def apply_theme(app: QApplication, theme: str = "dark"):
    """Apply theme to the application."""
    stylesheet = load_stylesheet(theme)
    app.setStyleSheet(stylesheet)
