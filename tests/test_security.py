"""Security tests: injections, traversal, filenames, export guards, log hygiene."""
import numpy as np
import pytest

from utils.security import (
    preview_text,
    sanitize_filename,
    validate_export_path,
    validate_input_path,
    validate_synthesis_text,
)

DANGEROUS_TEXTS = [
    "hello; rm -rf /",
    "$(whoami)",
    "`reboot`",
    "test && del C:\\Windows\\*",
    "<script>alert(1)</script>",
    "Robert'); DROP TABLE voices;--",
    "{{7*7}}",
    "${jndi:ldap://evil/x}",
    "%s%s%s%n",
    "\x00\x01\x02 control chars",
    "A" * 60_000,  # oversized
]


class TestSynthesisTextValidation:
    def test_dangerous_texts_do_not_raise_unexpectedly(self):
        # None of these may cause shell/code execution or crashes at
        # validation level — they are opaque data for the engines.
        for t in DANGEROUS_TEXTS[:-1]:
            assert validate_synthesis_text(t) == t.strip()

    def test_oversized_rejected(self):
        with pytest.raises(ValueError, match="too long"):
            validate_synthesis_text(DANGEROUS_TEXTS[-1])

    @pytest.mark.parametrize("bad", ["", "   ", "\n\t ", None])
    def test_empty_rejected(self, bad):
        with pytest.raises(ValueError):
            validate_synthesis_text(bad)


class TestFilenameSanitizing:
    @pytest.mark.parametrize("evil,expected_safe", [
        ("../secret", "secret"),
        ("..\\..\\win.ini", "win.ini"),
        ("a/b\\c", "c"),
        ('bad<>:"/\\|?*name', "___name"),
        ("  ...  ", "_"),
        ("", "tts"),
        ("ok_name-2024", "ok_name-2024"),
    ])
    def test_sanitize(self, evil, expected_safe):
        out = sanitize_filename(evil)
        assert out == expected_safe
        assert ".." not in out
        assert "/" not in out and "\\" not in out

    def test_long_name_truncated(self):
        assert len(sanitize_filename("x" * 200)) == 80


class TestExportPathGuards:
    def test_valid_wav(self, tmp_path):
        p = validate_export_path(str(tmp_path / "out.wav"), "wav")
        assert p.suffix == ".wav"

    def test_extension_mismatch(self, tmp_path):
        with pytest.raises(ValueError):
            validate_export_path(str(tmp_path / "out.mp3"), "wav")

    def test_bad_format(self, tmp_path):
        with pytest.raises(ValueError):
            validate_export_path(str(tmp_path / "out.ogg"), "ogg")

    def test_system_dir_refused(self, tmp_path):
        import os
        if os.name == "nt":
            target = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "tts_out.wav")
        else:
            target = "/etc/tts_out.wav"
        with pytest.raises(ValueError, match="system directory"):
            validate_export_path(target, "wav")


class TestInputPathGuards:
    def test_traversal_outside_allowed_ext_rejected(self, tmp_path):
        p = tmp_path / "evil.exe"
        p.write_text("x", encoding="utf-8")
        with pytest.raises(ValueError):
            validate_input_path(p)


class TestEnginesRejectInjections:
    def test_edge_unknown_voice(self):
        from tts.edge_tts_wrapper import EdgeTTSEngine
        eng = EdgeTTSEngine()
        eng._initialized = True
        with pytest.raises(RuntimeError):
            eng._validate_request("hello', evil='1", "evil-voice; rm -rf")

    def test_edge_empty_text(self):
        from tts.edge_tts_wrapper import EdgeTTSEngine
        eng = EdgeTTSEngine()
        eng._initialized = True
        with pytest.raises((RuntimeError, ValueError)):
            eng._validate_request("   ", "ru-RU-DmitryNeural")

    def test_supertonic_unknown_voice(self):
        from tts.supertonic_wrapper import SupertonicEngine
        eng = SupertonicEngine()
        eng._tts = object()  # bypass init, validation happens first
        with pytest.raises(RuntimeError):
            eng.synthesize("hello", "evil-voice")

    def test_export_worker_skips_empty_and_stopped(self, tmp_path):
        from audio.export import ExportWorker

        class FakeEngine:
            def __init__(self):
                self.calls = []

            def synthesize(self, text, voice_id, speed=1.0, pitch=1.0):
                self.calls.append(text)
                return np.zeros(100, dtype=np.float32), 22050

        out = tmp_path / "out.wav"
        worker = ExportWorker(FakeEngine(), ["   ", "Hello."], "v",
                              str(out), "wav", 1.0, 1.0)
        worker.run()  # synchronous
        assert out.exists()
        assert worker.tts_engine.calls == ["Hello."]


class TestLogHygiene:
    def test_preview_never_returns_full_text(self):
        secret = "S3CR3T-" + "x" * 500
        preview = preview_text(secret)
        assert "S3CR3T-" not in preview or len(preview) < 60
        assert "507 chars" in preview
        assert "chars" in preview

    def test_config_never_logs_values(self, caplog):
        import logging
        from unittest.mock import Mock, patch
        with patch("utils.config.QSettings") as mock_qs:
            inst = Mock()
            inst.value.return_value = None
            mock_qs.return_value = inst
            from utils.config import Config
            with caplog.at_level(logging.DEBUG, logger="utils.config"):
                cfg = Config()
                cfg.set("voice", "SECRET_VOICE_VALUE")
            for record in caplog.records:
                assert "SECRET_VOICE_VALUE" not in record.getMessage()
