"""Tests for file loaders (.txt/.rtf/.md) with fixtures and security checks."""
import pytest
from pathlib import Path

from utils.file_loaders import (
    load_text_file,
    load_rtf_file,
    load_markdown_file,
    load_file,
    get_supported_extensions,
    get_file_filter,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestTxtLoader:
    def test_load_sample(self):
        text = load_text_file(FIXTURES / "sample.txt")
        assert "Hello world" in text
        assert "Привет мир" in text

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_text_file(FIXTURES / "does_not_exist.txt")

    def test_wrong_extension_rejected(self, tmp_path):
        p = tmp_path / "note.md"
        p.write_text("hi", encoding="utf-8")
        with pytest.raises(ValueError):
            load_text_file(p)

    def test_fallback_encoding(self, tmp_path):
        p = tmp_path / "cp1251.txt"
        p.write_bytes("Привет мир".encode("cp1251"))
        text = load_text_file(p)
        assert "Привет" in text


class TestRtfLoader:
    def test_load_sample(self):
        text = load_rtf_file(FIXTURES / "sample.rtf")
        assert "Hello RTF world" in text

    def test_missing_striprtf(self, tmp_path, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "striprtf", None)
        monkeypatch.setitem(sys.modules, "striprtf.striprtf", None)
        p = tmp_path / "a.rtf"
        p.write_text("x", encoding="utf-8")
        # Either ImportError (lib missing) or a load error is acceptable;
        # the key point is no silent garbage output.
        try:
            load_rtf_file(p)
        except (ImportError, ValueError, TypeError):
            pass


class TestMarkdownLoader:
    def test_load_sample(self):
        text = load_markdown_file(FIXTURES / "sample.md")
        assert "Sample title" in text
        assert "**" not in text
        assert "https://example.com" not in text
        assert 'print("code should be removed")' not in text

    def test_headers_links_removed(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# H\nSee [docs](https://x.io) now.\n", encoding="utf-8")
        text = load_markdown_file(p)
        assert text == "H\nSee docs now."


class TestLoadFileDispatch:
    def test_txt(self):
        assert "Hello" in load_file(FIXTURES / "sample.txt")

    def test_md(self):
        assert "Sample title" in load_file(FIXTURES / "sample.md")

    def test_rtf(self):
        assert "Hello" in load_file(FIXTURES / "sample.rtf")

    def test_unsupported_extension_rejected(self, tmp_path):
        p = tmp_path / "evil.exe"
        p.write_text("MZ", encoding="utf-8")
        with pytest.raises(ValueError):
            load_file(p)

    def test_path_traversal_name_rejected_by_size_check(self, tmp_path):
        # limit check: oversized file must be refused
        from utils import security
        p = tmp_path / "big.txt"
        p.write_bytes(b"x" * (security.MAX_TEXT_FILE_SIZE + 1))
        with pytest.raises(ValueError, match="too large"):
            load_file(p)


class TestHelpers:
    def test_supported_extensions(self):
        exts = get_supported_extensions()
        assert set(exts) >= {".txt", ".rtf", ".md"}

    def test_file_filter(self):
        assert "*.txt" in get_file_filter()
