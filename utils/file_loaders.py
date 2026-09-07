"""File loaders for text files (.txt, .rtf, .md)."""
import re
from pathlib import Path

from utils.logger import get_logger
from utils.security import MAX_TEXT_FILE_SIZE, validate_input_path

logger = get_logger(__name__)


def _read_text_with_fallback(path: Path) -> str:
    """Read text trying UTF-8 first, then cp1251/latin-1 as fallback."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("File %s is not valid UTF-8, trying fallback encodings", path.name)
        for enc in ("cp1251", "latin-1"):
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, OSError):
                continue
        raise ValueError(f"Cannot decode file {path.name}: unsupported encoding")


def load_text_file(filepath):
    """Load plain text from .txt file."""
    path = validate_input_path(filepath)
    if path.suffix.lower() != ".txt":
        raise ValueError(f"Expected .txt file, got: {path.suffix!r}")
    return _read_text_with_fallback(path)


def load_rtf_file(filepath):
    """Load and convert RTF to plain text."""
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        raise ImportError("striprtf library is required to load RTF files. Install with: pip install striprtf")
    path = validate_input_path(filepath)
    if path.suffix.lower() != ".rtf":
        raise ValueError(f"Expected .rtf file, got: {path.suffix!r}")
    rtf_content = _read_text_with_fallback(path)
    if len(rtf_content) > MAX_TEXT_FILE_SIZE:
        raise ValueError("RTF file too large")
    return rtf_to_text(rtf_content)


def load_markdown_file(filepath):
    """Load markdown file and convert to plain text."""
    path = validate_input_path(filepath)
    if path.suffix.lower() not in (".md", ".markdown"):
        raise ValueError(f"Expected markdown file, got: {path.suffix!r}")
    content = _read_text_with_fallback(path)

    # Simple markdown to plain text conversion
    # Remove headers
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
    # Remove bold/italic markers
    content = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', content)
    content = re.sub(r'_{1,3}(.+?)_{1,3}', r'\1', content)
    # Remove links but keep text
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    # Remove images
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)
    # Remove code blocks
    content = re.sub(r'```[\s\S]*?```', '', content)
    content = re.sub(r'`(.+?)`', r'\1', content)
    # Remove blockquotes
    content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
    # Remove horizontal rules
    content = re.sub(r'^[-*_]{3,}\s*$', '', content, flags=re.MULTILINE)
    # Remove extra whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()


def load_file(filepath):
    """Load file based on extension (only supported types)."""
    path = Path(filepath)
    extension = path.suffix.lower()

    if extension == '.txt':
        return load_text_file(filepath)
    elif extension == '.rtf':
        return load_rtf_file(filepath)
    elif extension in ['.md', '.markdown']:
        return load_markdown_file(filepath)
    else:
        raise ValueError(
            f"Unsupported file type: {extension!r}. "
            f"Supported: {', '.join(get_supported_extensions())}"
        )


def get_supported_extensions():
    """Return list of supported file extensions."""
    return ['.txt', '.rtf', '.md', '.markdown']


def get_file_filter():
    """Return file filter string for file dialog."""
    return "Text Files (*.txt *.rtf *.md *.markdown);;All Files (*)"
