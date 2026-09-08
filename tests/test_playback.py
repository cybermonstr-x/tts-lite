"""Tests for PlaybackManager (fake engine/worker) and PlaybackWorker cleanup."""

import queue
import threading

import numpy as np
import pytest


class FakeEngine:
    stop_event = None

    def synthesize_streaming(self, text, voice_id, speed=1.0, pitch=1.0):
        yield np.zeros(2205, dtype=np.float32), 22050


class FakeWorker:
    """Drop-in stub for PlaybackWorker with real Qt signals behavior faked."""

    def __init__(self, *a, **k):
        self._volume = 1.0
        self.started = False
        self.stopped = False
        self.position_changed = _Sig()
        self.playback_finished = _Sig()
        self.error_occurred = _Sig()
        self.finished_event = threading.Event()
        self.finished_event.set()

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _Sig:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *a):
        for s in self._slots:
            s(*a)


@pytest.fixture()
def manager(monkeypatch):
    import audio.playback as pb

    monkeypatch.setattr(pb, "PlaybackWorker", FakeWorker)
    from audio.playback import PlaybackManager

    return PlaybackManager(FakeEngine())


class TestPlaybackManager:
    def test_no_sentences_error(self, manager, qtbot):
        with qtbot.waitSignal(manager.error_occurred, timeout=1000):
            manager.play()

    def test_no_voice_error(self, manager, qtbot):
        manager.set_sentences(["Hello."])
        with qtbot.waitSignal(manager.error_occurred, timeout=1000):
            manager.play()

    def test_play_starts_worker(self, manager):
        manager.set_sentences(["Hello.", "World."])
        manager.set_voice("v1")
        manager.play(0)
        assert manager._worker.started is True
        # is_playing may already be False if fake synthesis finished instantly;
        # at least worker must have been started
        assert manager._worker is not None
        manager.stop()

    def test_stop_emits(self, manager, qtbot):
        manager.set_sentences(["Hello."])
        manager.set_voice("v1")
        manager.play(0)
        with qtbot.waitSignal(manager.playback_stopped, timeout=1000):
            manager.stop()
        assert manager.is_playing is False

    def test_volume_speed_pitch_clamp(self, manager):
        manager.set_volume(5.0)
        assert manager._volume == 1.0
        manager.set_volume(-1.0)
        assert manager._volume == 0.0
        manager.set_speed(99.0)
        assert manager._speed == 2.0
        manager.set_pitch(0.0)
        assert manager._pitch == 0.5

    def test_preview_empty_error(self, manager, qtbot):
        with qtbot.waitSignal(manager.error_occurred, timeout=1000):
            manager.preview_selection("   ")

    def test_preview_plays(self, manager):
        manager.set_voice("v1")
        manager.preview_selection("Hello world. Second.")
        assert manager.total_sentences >= 1
        manager.stop()

    def test_synthesis_thread_joins_on_replay(self, manager):
        manager.set_sentences(["A."])
        manager.set_voice("v1")
        manager.play(0)
        manager.play(0)  # second play must clean up first without deadlock
        manager.stop()


class TestPlaybackWorkerReal:
    def test_stop_closes_stream(self, monkeypatch):
        import audio.playback as pb

        closed = {}

        class FakeStream:
            def start(self):
                pass

            def stop(self):
                closed["stop"] = True

            def close(self):
                closed["close"] = True

        class FakeSD:
            def OutputStream(self, **kwargs):
                assert kwargs["channels"] == 1
                return FakeStream()

        monkeypatch.setattr(pb, "sd", FakeSD())
        q = queue.Queue()
        worker = pb.PlaybackWorker(q, 22050)
        worker._stream = FakeStream()
        worker.stop()
        assert closed.get("stop") and closed.get("close")

    def test_volume_applied_once_in_callback(self, monkeypatch):
        import audio.playback as pb

        monkeypatch.setattr(pb, "sd", object())
        q = queue.Queue()
        worker = pb.PlaybackWorker(q, 22050)
        worker._volume = 0.5
        worker._is_playing = True
        worker._buffer = np.ones(4, dtype=np.float32)
        outdata = np.zeros((4, 1), dtype=np.float32)
        worker._audio_callback(outdata, 4, None, None)
        # volume applied exactly once: 1.0 * 0.5
        assert float(outdata[0, 0]) == pytest.approx(0.5)
