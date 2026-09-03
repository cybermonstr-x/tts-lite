"""File loaders for text files (.txt, .rtf, .md)."""
from pathlib import Path

def load_text_file(filepath):
    """Load plain text from .txt file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def load_rtf_file(filepath):
    """Load and convert RTF to plain text."""
    try:
        from striprtf.striprtf import rtf_to_text
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(path, 'r', encoding='utf-8') as f:
            rtf_content = f.read()
        
        return rtf_to_text(rtf_content)
    except ImportError:
        raise ImportError("striprtf library is required to load RTF files. Install with: pip install striprtf")

def load_markdown_file(filepath):
    """Load markdown file and convert to plain text."""
    import re
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
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
    """Load file based on extension."""
    path = Path(filepath)
    extension = path.suffix.lower()
    
    if extension == '.txt':
        return load_text_file(filepath)
    elif extension == '.rtf':
        return load_rtf_file(filepath)
    elif extension in ['.md', '.markdown']:
        return load_markdown_file(filepath)
    else:
        # Try to load as plain text
        return load_text_file(filepath)

def get_supported_extensions():
    """Return list of supported file extensions."""
    return ['.txt', '.rtf', '.md', '.markdown']

def get_file_filter():
    """Return file filter string for file dialog."""
    return "Text Files (*.txt *.rtf *.md *.markdown);;All Files (*)"
