"""UI tests for MainWindow: engine/voice selection, playback controls, theme/language."""
import pytest
import numpy as np
from unittest.mock import Mock, patch

pytestmark = pytest.mark.ui


def _mock_config(**overrides):
    cfg = Mock()
    cfg.theme = overrides.get("theme", "dark")
    cfg.language = overrides.get("language", "ru")
    cfg.volume = overrides.get("volume", 80)
    cfg.speed = overrides.get("speed", 1.0)
    cfg.pitch = overrides.get("pitch", 1.0)
    cfg.voice = overrides.get("voice", "ru_RU-irina-medium")
    cfg.last_voice = cfg.voice
    cfg.last_engine = overrides.get("last_engine", "piper")
    cfg.engine = overrides.get("engine", "piper")
    cfg.last_directory = overrides.get("last_directory", "")
    cfg.edge_consent = overrides.get("edge_consent", "accepted")
    cfg.get.side_effect = lambda k, d=None: getattr(cfg, k, d)
    cfg.set = Mock()
    cfg.save = Mock()
    cfg.config_file_path.return_value = ""
    cfg.validate.return_value = True
    def _set_edge(v):
        cfg.edge_consent = "accepted" if v else "declined"
    cfg.set_edge_consent.side_effect = _set_edge
    return cfg


def _fake_engine():
    from tts.engine import VoiceInfo
    eng = Mock()
    eng.get_voices.return_value = [
        VoiceInfo(id="v1", name="Voice 1", language="ru", gender="male"),
        VoiceInfo(id="v2", name="Voice 2", language="en", gender="female"),
    ]
    eng.initialize.return_value = True
    eng.is_available.return_value = True
    eng.synthesize.return_value = (np.zeros(10, dtype=np.float32), 22050)
    eng.synthesize_streaming.return_value = iter([(np.zeros(10, dtype=np.float32), 22050)])
    eng.stop_event = None
    eng.stop = Mock()
    return eng


@pytest.fixture()
def window(qtbot, monkeypatch):
    cfg = _mock_config()
    from utils.translations import Translations
    from ui.main_window import MainWindow

    fake_eng = _fake_engine()
    monkeypatch.setattr("tts.engine.create_engine", lambda n="auto": fake_eng)
    monkeypatch.setattr("tts.engine.get_available_engines", lambda: ["piper", "edge_tts", "supertonic"])
    monkeypatch.setattr("ui.main_window.apply_theme", lambda app, t: None)

    # Mock PlaybackManager / AudioExporter to avoid real audio threads
    import audio.playback as pb_mod
    import audio.export as ex_mod

    fake_pm = Mock()
    fake_pm.is_playing = False
    for sig in ("playback_started", "playback_stopped", "playback_finished",
                "position_changed", "progress_updated", "error_occurred"):
        m = Mock()
        m.connect = Mock()
        setattr(fake_pm, sig, m)
    fake_pm.play = Mock()
    fake_pm.stop = Mock()

    fake_exp = Mock()
    for sig in ("export_started", "export_progress", "export_progress_text",
                "export_complete", "export_error"):
        m = Mock()
        m.connect = Mock()
        setattr(fake_exp, sig, m)

    monkeypatch.setattr(pb_mod, "PlaybackManager", lambda eng, parent=None: fake_pm)
    monkeypatch.setattr(ex_mod, "AudioExporter", lambda eng, parent=None: fake_exp)
    import ui.main_window as mw_mod
    monkeypatch.setattr(mw_mod, "PlaybackManager", lambda eng, parent=None: fake_pm)
    monkeypatch.setattr(mw_mod, "AudioExporter", lambda eng, parent=None: fake_exp)

    trans = Translations("ru")
    win = MainWindow(cfg, trans)
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win, timeout=2000)
    yield win
    try:
        win.close()
    except Exception:
        pass


class TestMainWindowCreation:
    def test_creates(self, window):
        assert window is not None
        assert window.engine_combo.count() >= 1
        assert window.voice_combo.count() >= 1

    def test_volume_slider(self, window):
        window.vol_slider.setValue(42)
        assert window.config.volume == 42

    def test_speed_slider(self, window):
        window.spd_slider.setValue(150)
        assert abs(window.config.speed - 1.5) < 1e-6

    def test_pitch_slider(self, window):
        window.pitch_slider.setValue(120)
        assert abs(window.config.pitch - 1.2) < 1e-6

    def test_theme_switch(self, window, monkeypatch):
        called = {}
        monkeypatch.setattr("ui.main_window.apply_theme", lambda app, t: called.__setitem__("theme", t))
        window.theme_combo.setCurrentIndex(1)
        assert window.config.theme == "light"
        assert called.get("theme") == "light"


class TestLanguageSwitch:
    def test_cancel_keeps_old(self, window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
        old = window.config.language
        window.lang_combo.setCurrentIndex(1 if old == "ru" else 0)
        assert window.config.language == old

    def test_accept_saves(self, window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtWidgets import QApplication
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr("ui.main_window.subprocess.Popen", Mock())
        monkeypatch.setattr(QApplication, "quit", Mock())
        old = window.config.language
        target = "en" if old == "ru" else "ru"
        window.lang_combo.setCurrentIndex(1 if old == "ru" else 0)
        assert window.config.language == target


class TestPlaybackActions:
    def test_play_empty_warns(self, window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, "warning", Mock())
        window.text_edit.setPlainText("   ")
        window._on_play()
        QMessageBox.warning.assert_called()

    def test_preview_no_selection_warns(self, window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, "warning", Mock())
        window.text_edit.setPlainText("Hello world")
        cursor = window.text_edit.textCursor()
        cursor.clearSelection()
        window.text_edit.setTextCursor(cursor)
        window._on_preview()
        QMessageBox.warning.assert_called()

    def test_edge_consent_blocks(self, window, monkeypatch):
        # Patch consent check BEFORE triggering engine combo signal
        monkeypatch.setattr("tts.edge_tts_wrapper.check_edge_consent", lambda cfg, parent=None: False)
        monkeypatch.setattr("ui.main_window.check_edge_consent", lambda cfg, parent=None: False, raising=False)
        window.config.edge_consent = "unknown"
        idx = -1
        for i in range(window.engine_combo.count()):
            if window.engine_combo.itemData(i) == "edge_tts":
                idx = i
                break
        if idx == -1:
            window.engine_combo.blockSignals(True)
            window.engine_combo.addItem("Edge TTS (online)", "edge_tts")
            window.engine_combo.blockSignals(False)
            idx = window.engine_combo.count() - 1
        window.text_edit.setPlainText("Hello")
        pm_play = window.playback_manager.play
        # Directly test _require_edge_consent_for_playback path via _on_play
        # without changing combo (avoids dialog). Simulate Edge being selected
        # by temporarily lying about currentData
        monkeypatch.setattr(window, "_current_engine_name", lambda: "edge_tts")
        window._on_play()
        pm_play.assert_not_called()

    def test_stop_safe(self, window):
        # Must not raise even when called twice
        window._on_stop()
        window._on_stop()


class TestExportAction:
    def test_export_empty_warns(self, window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, "warning", Mock())
        window.text_edit.setPlainText("  ")
        window._on_export()
        QMessageBox.warning.assert_called()

    def test_save_as_no_temp(self, window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, "information", Mock())
        window._temp_audio_path = None
        window._on_save_as()
        QMessageBox.information.assert_not_called()
