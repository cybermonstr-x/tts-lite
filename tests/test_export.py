"""Tests for audio export (fake engine, real WAV output, guards)."""

import wave

import numpy as np

from audio.export import AudioExporter, ExportWorker


class FakeEngine:
    def __init__(self, sr=22050):
        self.sr = sr
        self.calls = []

    def synthesize(self, text, voice_id, speed=1.0, pitch=1.0):
        self.calls.append(text)
        return np.zeros(2205, dtype=np.float32), self.sr


def _read_wav(path):
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes(), wf.getframerate()


class TestExportWorker:
    def test_wav_export(self, tmp_path):
        out = tmp_path / "out.wav"
        worker = ExportWorker(
            FakeEngine(), ["Hello.", "World."], "v", str(out), "wav", 1.0, 1.0
        )
        worker.run()
        assert out.exists()
        frames, sr = _read_wav(out)
        assert frames == 2205 * 2 and sr == 22050

    def test_skips_empty_sentences(self, tmp_path):
        eng = FakeEngine()
        out = tmp_path / "out.wav"
        ExportWorker(eng, ["  ", "Hi."], "v", str(out), "wav", 1.0, 1.0).run()
        assert eng.calls == ["Hi."]

    def test_cancel_stops(self, tmp_path):
        out = tmp_path / "out.wav"
        worker = ExportWorker(FakeEngine(), ["Hi."], "v", str(out), "wav", 1.0, 1.0)
        worker.cancel()
        worker.run()
        assert not out.exists()

    def test_bad_format_rejected(self, tmp_path):
        out = tmp_path / "out.ogg"
        worker = ExportWorker(FakeEngine(), ["Hi."], "v", str(out), "ogg", 1.0, 1.0)
        errors = []
        worker.error_occurred.connect(errors.append)
        worker.run()
        assert errors

    def test_system_dir_rejected(self):
        import os

        target = (
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "x.wav")
            if os.name == "nt"
            else "/etc/x.wav"
        )
        worker = ExportWorker(FakeEngine(), ["Hi."], "v", target, "wav", 1.0, 1.0)
        errors = []
        worker.error_occurred.connect(errors.append)
        worker.run()
        assert errors

    def test_stopped_synthesis_aborts(self, tmp_path):
        class StopEngine:
            def synthesize(self, *a, **k):
                return None

        out = tmp_path / "out.wav"
        ExportWorker(StopEngine(), ["Hi."], "v", str(out), "wav", 1.0, 1.0).run()
        assert not out.exists()

    def test_mp3_fallback_to_wav_without_pydub(self, tmp_path, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "pydub", None)
        out = tmp_path / "out.mp3"
        worker = ExportWorker(FakeEngine(), ["Hi."], "v", str(out), "mp3", 1.0, 1.0)
        worker.run()
        # Falls back to wav next to the requested path.
        assert (tmp_path / "out.wav").exists()


class TestAudioExporter:
    def test_rejects_empty(self, qtbot):
        exp = AudioExporter(FakeEngine())
        with qtbot.waitSignal(exp.export_error, timeout=1000):
            exp.export_to_file([], "v", "x.wav")

    def test_rejects_bad_format(self, qtbot):
        exp = AudioExporter(FakeEngine())
        with qtbot.waitSignal(exp.export_error, timeout=1000):
            exp.export_to_file(["Hi."], "v", "x.ogg", format_type="ogg")

    def test_rejects_no_voice(self, qtbot):
        exp = AudioExporter(FakeEngine())
        with qtbot.waitSignal(exp.export_error, timeout=1000):
            exp.export_to_file(["Hi."], "", "x.wav")

    def test_rejects_system_path(self, qtbot):
        import os

        exp = AudioExporter(FakeEngine())
        target = (
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "x.wav")
            if os.name == "nt"
            else "/etc/x.wav"
        )
        with qtbot.waitSignal(exp.export_error, timeout=1000):
            exp.export_to_file(["Hi."], "v", target, format_type="wav")
