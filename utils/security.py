"""Central security helpers: path validation, filename sanitizing, log preview.

All user-controlled paths and texts must go through these helpers before
use in file/network/audio operations.
"""
import os
import re
from pathlib import Path

# Max size for user-loaded text files (10 MB) — protects from memory exhaustion.
MAX_TEXT_FILE_SIZE = 10 * 1024 * 1024
# Max text length for a single synthesis request (Edge TTS chunks internally).
MAX_SYNTHESIS_CHARS = 50_000

_ALLOWED_EXPORT_FORMATS = {"mp3", "wav"}
_ALLOWED_TEXT_EXTENSIONS = {".txt", ".rtf", ".md", ".markdown"}

# Directories that must never be used as export targets.
_BLOCKED_EXPORT_DIRS = {
    Path(p) for p in (
        os.environ.get("SystemRoot", r"C:\Windows") if os.name == "nt" else "/",
    )
}
_SYSTEM_DIRS_NT = (
    os.environ.get("SystemRoot", r"C:\Windows").lower(),
    os.environ.get("windir", r"C:\Windows").lower(),
)
_SYSTEM_DIRS_POSIX = ("/bin", "/sbin", "/usr/bin", "/usr/sbin", "/etc", "/sys", "/proc")


def preview_text(text: str, max_chars: int = 10) -> str:
    """Return a safe short preview for logging (never the full user text)."""
    if not text:
        return "<empty>"
    preview = text[:max_chars].replace("\n", " ").replace("\r", " ")
    return f"'{preview}...' ({len(text)} chars)" if len(text) > max_chars else f"'{preview}'"


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Strip dangerous characters from a file name stem.

    Removes path separators (both / and \\), ``..``, control chars and
    OS-reserved symbols. Returns ``'tts'`` if nothing safe remains.
    """
    if not name:
        return "tts"
    # Drop any directory components first (defence against '../' input).
    # Handle both Unix and Windows path separators on all platforms.
    name = name.replace('\\', '/').split('/')[-1]
    # Replace reserved/special chars with underscore.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.replace("..", "_")
    name = name.strip(" .")
    if not name:
        return "tts"
    return name[:max_len]


def validate_input_path(filepath: str | os.PathLike) -> Path:
    """Validate a user-selected input file path.

    Raises:
        ValueError: on unsupported extension, oversized file or missing file.
    """
    path = Path(filepath)
    if path.suffix.lower() not in _ALLOWED_TEXT_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix!r}")
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")
    try:
        size = path.stat().st_size
    except OSError as e:
        raise ValueError(f"Cannot access file: {e}")
    if size > MAX_TEXT_FILE_SIZE:
        raise ValueError(
            f"File too large ({size} bytes, max {MAX_TEXT_FILE_SIZE})"
        )
    return path


def validate_export_path(output_path: str | os.PathLike, fmt: str) -> Path:
    """Validate an export destination path.

    Guards against writing into OS system directories and against
    path-traversal tricks. Creates the parent directory if needed.

    Raises:
        ValueError: if the path/format is unsafe.
    """
    if fmt not in _ALLOWED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {fmt!r}")
    path = Path(output_path).resolve()
    if path.suffix.lower() != f".{fmt}":
        raise ValueError(f"Output extension must be .{fmt}")
    resolved = str(path).lower()
    if os.name == "nt":
        for sysdir in _SYSTEM_DIRS_NT:
            if resolved == sysdir or resolved.startswith(sysdir + os.sep):
                raise ValueError(f"Export into system directory is forbidden: {path}")
    else:
        for sysdir in _SYSTEM_DIRS_POSIX:
            if str(path) == sysdir or str(path).startswith(sysdir + "/"):
                raise ValueError(f"Export into system directory is forbidden: {path}")
    # Refuse to overwrite critical system files by extension/behaviour is
    # covered by the directory check above; still ensure parent is writable.
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Cannot create export directory: {e}")
    return path


def validate_synthesis_text(text: str) -> str:
    """Validate user text before sending it to a TTS engine.

    Returns the stripped text. Raises ValueError on empty/oversized input.
    The text itself is passed opaquely to the engine libraries (no shell
    invocation anywhere), so no escaping is needed — only length checks.
    """
    if text is None:
        raise ValueError("Text is empty")
    stripped = text.strip()
    if not stripped:
        raise ValueError("Text is empty")
    if len(stripped) > MAX_SYNTHESIS_CHARS:
        raise ValueError(
            f"Text too long ({len(stripped)} chars, max {MAX_SYNTHESIS_CHARS})"
        )
    return stripped
