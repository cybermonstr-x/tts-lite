"""Tests for Supertonic wrapper (mocked TTS backend)."""
import io
import wave
import pytest
import numpy as np

from tts.supertonic_wrapper import SupertonicEngine, is_supertonic_downloaded


class FakeTTS:
    def __init__(self, wav_payload):
        self._payload = wav_payload

    def get_voice_style(self, voice_name):
        assert voice_name in {v.id for v in SupertonicEngine.VOICES}
        return f"style:{voice_name}"

    def synthesize(self, text, lang, voice_style, total_steps, speed):
        assert lang == "na"
        assert 0.7 <= speed <= 2.0
        return self._payload, 1.0


def _wav_bytes(samples=4410, sr=44100):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((np.zeros(samples, dtype=np.int16)).tobytes())
    return buf.getvalue()


class TestVoices:
    def test_ten_voices(self):
        assert len(SupertonicEngine.VOICES) == 10

    def test_is_available_missing(self, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "supertonic", None)
        # module present but broken -> import returns None, attribute access fails
        eng = SupertonicEngine()
        eng._available = None
        # force ImportError path
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name == "supertonic":
                raise ImportError("nope")
            return real_import(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        assert eng.is_available() is False


class TestSynthesize:
    def test_numpy_path_resampled(self):
        eng = SupertonicEngine()
        eng._tts = FakeTTS(np.zeros((1, 4410), dtype=np.float32))
        audio, sr = eng.synthesize("Hello", "M1")
        assert sr == 22050
        assert len(audio) == 2205

    def test_bytes_path(self):
        eng = SupertonicEngine()
        eng._tts = FakeTTS(_wav_bytes())
        audio, sr = eng.synthesize("Hello", "F1")
        assert sr == 22050
        assert len(audio) > 0

    def test_streaming_single_chunk(self):
        eng = SupertonicEngine()
        eng._tts = FakeTTS(np.zeros((1, 4410), dtype=np.float32))
        chunks = list(eng.synthesize_streaming("Hi", "M2"))
        assert len(chunks) == 1

    def test_not_initialized(self):
        eng = SupertonicEngine()
        with pytest.raises(RuntimeError):
            eng.synthesize("hi", "M1")

    def test_unknown_voice(self):
        eng = SupertonicEngine()
        eng._tts = FakeTTS(np.zeros(10, dtype=np.float32))
        with pytest.raises(RuntimeError):
            eng.synthesize("hi", "EVIL")

    def test_empty_text(self):
        eng = SupertonicEngine()
        eng._tts = FakeTTS(np.zeros(10, dtype=np.float32))
        with pytest.raises((RuntimeError, ValueError)):
            eng.synthesize("   ", "M1")


class TestDownloadHelpers:
    def test_not_downloaded_empty_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path / "nothing"))
        assert is_supertonic_downloaded() is False
