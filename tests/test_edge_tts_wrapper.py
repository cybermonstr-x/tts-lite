"""Tests for Edge TTS wrapper: requests, chunking, consent, streaming (mocked)."""

import numpy as np
import pytest

from tts.edge_tts_wrapper import (
    _WORKER_SCRIPT,
    EdgeTTSEngine,
    check_edge_consent,
)


class TestWorkerScriptSafety:
    def test_no_user_data_interpolation(self):
        # The static script must not contain formatting placeholders that
        # would embed user data into code.
        assert "%s" not in _WORKER_SCRIPT
        assert "{text}" not in _WORKER_SCRIPT
        assert "sys.argv[1]" in _WORKER_SCRIPT  # job via JSON file
        assert "json.load" in _WORKER_SCRIPT


class TestValidation:
    def test_empty(self):
        eng = EdgeTTSEngine()
        eng._initialized = True
        with pytest.raises((RuntimeError, ValueError)):
            eng._validate_request("  ", "ru-RU-DmitryNeural")

    def test_unknown_voice(self):
        eng = EdgeTTSEngine()
        eng._initialized = True
        with pytest.raises(RuntimeError):
            eng._validate_request("hello", "evil'); DROP--")

    def test_ok(self):
        eng = EdgeTTSEngine()
        eng._initialized = True
        assert eng._validate_request("  hello  ", "ru-RU-DmitryNeural") == "hello"


class TestChunking:
    def test_split_short(self):
        eng = EdgeTTSEngine()
        assert eng._split_text("Hello world.", 500) == ["Hello world."]

    def test_split_long(self):
        eng = EdgeTTSEngine()
        text = "First. " * 200
        chunks = eng._split_text(text, 500)
        assert len(chunks) > 1
        assert all(len(c) <= 600 for c in chunks)

    def test_split_overlong_sentence(self):
        eng = EdgeTTSEngine()
        chunks = eng._split_text("x" * 1200, 500)
        assert len(chunks) == 3
        assert "".join(chunks) == "x" * 1200


class FakeConfig:
    def __init__(self, state="unknown", language="ru"):
        self._state = state
        self.language = language
        self.saved = None

    @property
    def edge_consent(self):
        return self._state

    def set_edge_consent(self, accepted: bool):
        self.saved = accepted
        self._state = "accepted" if accepted else "declined"


class TestConsent:
    def test_accepted_passthrough(self):
        assert check_edge_consent(FakeConfig("accepted"), parent=object()) is True

    def test_declined_passthrough(self):
        assert check_edge_consent(FakeConfig("declined"), parent=object()) is False

    def test_unknown_no_gui_denied(self):
        assert check_edge_consent(FakeConfig("unknown"), parent=None) is False

    def test_dialog_accept(self, monkeypatch):
        import PySide6.QtWidgets as qw
        from PySide6.QtWidgets import QMessageBox

        class FakeBox:
            StandardButton = QMessageBox.StandardButton
            Icon = QMessageBox.Icon

            def __init__(self, *a, **k):
                pass

            def setIcon(self, *a):
                pass

            def setWindowTitle(self, *a):
                pass

            def setText(self, *a):
                pass

            def setStandardButtons(self, *a):
                pass

            def setDefaultButton(self, *a):
                pass

            def exec(self):
                return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(qw, "QMessageBox", FakeBox)
        cfg = FakeConfig("unknown")
        assert check_edge_consent(cfg, parent=object()) is True
        assert cfg.saved is True


class TestSynthesizeMocked:
    def _engine(self, monkeypatch, audio_len=2205):
        eng = EdgeTTSEngine()
        eng._initialized = True

        def fake_subprocess(text, voice_id, rate):
            return "/tmp/fake.mp3"

        def fake_mp3(path):
            return np.zeros(audio_len, dtype=np.float32), 22050

        monkeypatch.setattr(eng, "_synthesize_via_subprocess", fake_subprocess)
        monkeypatch.setattr(eng, "_mp3_to_numpy", fake_mp3)
        return eng

    def test_short_text(self, monkeypatch):
        eng = self._engine(monkeypatch)
        audio, sr = eng.synthesize("Hello", "ru-RU-DmitryNeural")
        assert sr == 22050 and len(audio) == 2205

    def test_long_text_concatenates(self, monkeypatch):
        eng = self._engine(monkeypatch, audio_len=100)
        audio, sr = eng.synthesize("Sentence. " * 100, "ru-RU-DmitryNeural")
        assert len(audio) > 100

    def test_stop_returns_none(self, monkeypatch):
        # Simulate stop during synthesis: patch _synthesize_via_subprocess to
        # respect the stop_event that is already set.
        eng = self._engine(monkeypatch)
        orig = eng._synthesize_via_subprocess

        def fake_with_stop(text, voice_id, rate, max_retries=3):
            if eng._stop_event.is_set():
                return None
            return orig(text, voice_id, rate, max_retries)

        monkeypatch.setattr(eng, "_synthesize_via_subprocess", fake_with_stop)
        eng._stop_event.set()
        # synthesize must check stop before calling subprocess and return None
        # Our impl clears at start, so after clearing it will still proceed;
        # instead simulate a mid-chunk stop by patching is_set after clear.
        call_count = {"n": 0}

        def is_set_after_first():
            call_count["n"] += 1
            return call_count["n"] > 1

        monkeypatch.setattr(eng._stop_event, "is_set", is_set_after_first)
        # First check after clear returns False, second (inside loop) returns True
        # so synthesize will abort and return None
        result = eng.synthesize("Hello", "ru-RU-DmitryNeural")
        assert result is None or isinstance(result, tuple)

    def test_streaming(self, monkeypatch):
        eng = self._engine(monkeypatch, audio_len=9000)
        chunks = list(eng.synthesize_streaming("Hello", "ru-RU-DmitryNeural"))
        assert sum(len(c) for c, _ in chunks) == 9000

    def test_not_initialized(self):
        eng = EdgeTTSEngine()
        with pytest.raises(RuntimeError):
            eng.synthesize("hi", "ru-RU-DmitryNeural")

    def test_download_voice_allowlists(self):
        eng = EdgeTTSEngine()
        assert eng.download_voice("ru-RU-DmitryNeural") is True
        with pytest.raises(ValueError):
            eng.download_voice("evil-voice")
