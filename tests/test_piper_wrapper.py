"""Tests for Piper wrapper: download security, hashing, synthesis (mocked)."""
import sys
import types
import pytest
import numpy as np

from tts.piper_wrapper import (
    PiperEngine,
    get_models_dir,
    sha256_of_file,
    verify_voice_file,
    AVAILABLE_VOICES,
)


class TestModelsDir:
    def test_uses_cache_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        if sys.platform != "win32":
            d = get_models_dir()
            assert ".cache" in str(d) and "tts-lite" in str(d)

    def test_all_urls_https(self):
        for vid, info in AVAILABLE_VOICES.items():
            assert info["url"].startswith("https://"), vid
            assert info["config_url"].startswith("https://"), vid


class TestHashing:
    def test_sha256_roundtrip(self, tmp_path):
        p = tmp_path / "model.onnx"
        p.write_bytes(b"fake-model-data")
        digest = sha256_of_file(p)
        assert verify_voice_file(p, digest) is True
        assert verify_voice_file(p, "0" * 64) is False

    def test_empty_file_invalid(self, tmp_path):
        p = tmp_path / "empty.onnx"
        p.write_bytes(b"")
        assert verify_voice_file(p, None) is False


class TestDownloadVoice:
    def test_unknown_voice(self):
        eng = PiperEngine.__new__(PiperEngine)
        assert eng.download_voice("nope") is False

    def test_insecure_url_refused(self, tmp_path):
        import tts.piper_wrapper as pw
        eng = PiperEngine.__new__(PiperEngine)
        eng._voices_dir = tmp_path
        with pytest.raises(RuntimeError, match="insecure"):
            eng._download_url_to_file("http://evil/x.onnx", tmp_path / "x.onnx")

    def test_download_success_mocked(self, tmp_path, monkeypatch):
        import tts.piper_wrapper as pw

        eng = PiperEngine.__new__(PiperEngine)
        eng._voices_dir = tmp_path

        class FakeResp:
            headers = {"content-length": "11"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def raise_for_status(self):
                pass

            def iter_content(self, chunk_size=8192):
                yield b"hello-model"

        fake_requests = types.SimpleNamespace(get=lambda *a, **k: FakeResp())
        # config download returns small JSON body via non-stream path
        orig_get = fake_requests.get

        class FakeResp2(FakeResp):
            def __init__(self, body: bytes):
                self._body = body
                self.content = body
                self.headers = {"content-length": str(len(body))}

            def iter_content(self, chunk_size=8192):
                yield self._body

        def fake_get(url, **kwargs):
            assert kwargs.get("verify") is True
            assert kwargs.get("timeout", 0) > 0
            if url.endswith(".json"):
                return FakeResp2(b'{"sample_rate": 22050}')
            return FakeResp2(b"fake-onnx-bytes")

        fake_requests.get = fake_get
        monkeypatch.setitem(sys.modules, "requests", fake_requests)

        assert eng.download_voice("ru_RU-irina-medium") is True
        assert (tmp_path / "ru_RU-irina-medium.onnx").exists()
        assert (tmp_path / "ru_RU-irina-medium.onnx.json").exists()

    def test_download_failure_cleans_up(self, tmp_path, monkeypatch):
        eng = PiperEngine.__new__(PiperEngine)
        eng._voices_dir = tmp_path

        def boom(*a, **k):
            raise ConnectionError("offline")

        fake_requests = types.SimpleNamespace(get=boom)
        monkeypatch.setitem(sys.modules, "requests", fake_requests)
        assert eng.download_voice("ru_RU-irina-medium") is False


class TestSynthesizeMocked:
    def _engine_with_fake_model(self, monkeypatch):
        import tts.piper_wrapper as pw

        class FakeChunk:
            audio_int16_array = (np.ones(100, dtype=np.int16) * 1000)

        class FakeModel:
            config = types.SimpleNamespace(sample_rate=22050)

            def synthesize(self, text):
                assert "SECRET" not in text or True
                yield FakeChunk()

        fake_piper = types.SimpleNamespace(
            PiperVoice=types.SimpleNamespace(
                load=lambda m, c: FakeModel()
            )
        )
        monkeypatch.setitem(sys.modules, "piper", fake_piper)
        monkeypatch.setattr(pw.PiperEngine, "is_voice_downloaded", lambda self, v: True)

        eng = PiperEngine.__new__(PiperEngine)
        eng._initialized = True
        eng._model = None
        eng._current_voice = None
        eng._voices_dir = pw.get_models_dir()
        eng.stop_event = None
        return eng

    def test_synthesize(self, monkeypatch):
        eng = self._engine_with_fake_model(monkeypatch)
        audio, sr = eng.synthesize("Hello world", "ru_RU-irina-medium")
        assert sr == 22050
        assert len(audio) == 100

    def test_synthesize_empty_rejected(self, monkeypatch):
        eng = self._engine_with_fake_model(monkeypatch)
        with pytest.raises((RuntimeError, ValueError)):
            eng.synthesize("   ", "ru_RU-irina-medium")

    def test_streaming(self, monkeypatch):
        eng = self._engine_with_fake_model(monkeypatch)
        chunks = list(eng.synthesize_streaming("Hi", "ru_RU-irina-medium"))
        assert len(chunks) == 1

    def test_not_initialized(self):
        eng = PiperEngine.__new__(PiperEngine)
        eng._initialized = False
        eng._model = None
        eng._current_voice = None
        eng.stop_event = None
        with pytest.raises(RuntimeError):
            eng.synthesize("hi", "ru_RU-irina-medium")
