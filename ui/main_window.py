"""Main application window."""
import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPlainTextEdit, QPushButton, QLabel, QComboBox, QSlider,
    QProgressBar, QGroupBox, QMenuBar, QMenu, QStatusBar,
    QFileDialog, QMessageBox, QApplication, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont

from utils.config import Config
from utils.translations import Translations
from utils.file_loaders import load_file, get_file_filter
from utils.text_processing import split_into_sentences, get_text_statistics
from tts.engine import create_engine
from audio.playback import PlaybackManager
from audio.export import AudioExporter
from ui.styles import apply_theme

APP_VERSION = "1.0.4"

def _get_music_folder():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        music_dir = winreg.QueryValueEx(key, "My Music")[0]
        winreg.CloseKey(key)
        return music_dir
    except Exception:
        pass
    return str(Path.home() / "Music")

class MainWindow(QMainWindow):
    def __init__(self, config: Config, translations: Translations):
        super().__init__()
        
        self.config = config
        self.translations = translations
        self.tts_engine = None
        self.playback_manager = None
        self.exporter = None
        self._temp_audio_path = None
        self._music_folder = _get_music_folder()
        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._elapsed_seconds = 0
        self._export_start_time = 0.0
        self._current_file = None
        
        self._init_ui()
        self._init_tts()
        self._init_playback()
        self._load_settings()
        self._load_default_text()

        apply_theme(QApplication.instance(), self.config.theme)
    
    def _init_ui(self):
        t = self.translations
        self.setWindowTitle(t.t("app_title"))
        self.setMinimumSize(1200, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel
        left = QWidget()
        left.setMinimumWidth(400)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(t.t("placeholder_text"))
        self.text_edit.setFont(QFont("Consolas", 11))
        self.text_edit.textChanged.connect(self._update_stats)
        self.text_edit.selectionChanged.connect(self._update_preview_btn)
        left_layout.addWidget(self.text_edit)
        
        self.stats_label = QLabel("")
        left_layout.addWidget(self.stats_label)
        self._update_stats()
        
        splitter.addWidget(left)
        
        # Right panel with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(350)
        
        right = self._create_right_panel()
        scroll.setWidget(right)
        splitter.addWidget(scroll)
        
        splitter.setSizes([500, 350])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setHandleWidth(6)
        
        self._create_menu()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(t.t("ready"))
    
    def _create_right_panel(self) -> QWidget:
        t = self.translations
        panel = QWidget()
        panel.setMinimumWidth(380)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Engine
        g = QGroupBox(t.t("engine"))
        gl = QVBoxLayout(g)
        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumHeight(36)
        self.engine_combo.setToolTip(t.t("tooltip_engine"))
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        gl.addWidget(self.engine_combo)
        layout.addWidget(g)
        
        # Voice
        g = QGroupBox(t.t("voice"))
        gl = QVBoxLayout(g)
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumHeight(36)
        self.voice_combo.setToolTip(t.t("tooltip_voice"))
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        gl.addWidget(self.voice_combo)
        self.voice_status_label = QLabel("")
        self.voice_status_label.setWordWrap(True)
        self.voice_status_label.setStyleSheet("color: #f59e0b; font-size: 11px;")
        gl.addWidget(self.voice_status_label)
        layout.addWidget(g)
        
        # Audio
        g = QGroupBox(t.t("audio"))
        gl = QVBoxLayout(g)
        gl.setSpacing(4)
        
        row = QHBoxLayout()
        row.addWidget(QLabel(t.t("volume") + ":"))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setSingleStep(1)
        self.vol_slider.setValue(self.config.volume)
        self.vol_slider.setToolTip(t.t("tooltip_volume"))
        self.vol_label = QLabel(f"{self.config.volume}%")
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        row.addWidget(self.vol_slider)
        row.addWidget(self.vol_label)
        gl.addLayout(row)
        
        row = QHBoxLayout()
        row.addWidget(QLabel(t.t("speed") + ":"))
        self.spd_slider = QSlider(Qt.Orientation.Horizontal)
        self.spd_slider.setRange(50, 200)
        self.spd_slider.setSingleStep(1)
        self.spd_slider.setValue(int(self.config.speed * 100))
        self.spd_slider.setToolTip(t.t("tooltip_speed"))
        self.spd_label = QLabel(f"{self.config.speed:.2f}x")
        self.spd_slider.valueChanged.connect(self._on_spd_changed)
        row.addWidget(self.spd_slider)
        row.addWidget(self.spd_label)
        gl.addLayout(row)
        
        row = QHBoxLayout()
        row.addWidget(QLabel(t.t("pitch") + ":"))
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(50, 200)
        self.pitch_slider.setSingleStep(1)
        self.pitch_slider.setValue(int(self.config.pitch * 100))
        self.pitch_slider.setToolTip(t.t("tooltip_pitch"))
        self.pitch_label = QLabel(f"{self.config.pitch:.2f}x")
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)
        row.addWidget(self.pitch_slider)
        row.addWidget(self.pitch_label)
        gl.addLayout(row)
        
        layout.addWidget(g)
        
        # Playback
        g = QGroupBox(t.t("playback"))
        gl = QVBoxLayout(g)
        row = QHBoxLayout()
        self.play_btn = QPushButton(t.t("play"))
        self.play_btn.setObjectName("playButton")
        self.play_btn.setMinimumHeight(40)
        self.play_btn.setToolTip(t.t("tooltip_play"))
        self.play_btn.clicked.connect(self._on_play)
        row.addWidget(self.play_btn)
        self.stop_btn = QPushButton(t.t("stop"))
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setToolTip(t.t("tooltip_stop"))
        self.stop_btn.clicked.connect(self._on_stop)
        row.addWidget(self.stop_btn)
        gl.addLayout(row)
        self.preview_btn = QPushButton(t.t("preview"))
        self.preview_btn.setMinimumHeight(40)
        self.preview_btn.setToolTip(t.t("tooltip_preview"))
        self.preview_btn.clicked.connect(self._on_preview)
        gl.addWidget(self.preview_btn)
        layout.addWidget(g)
        
        # Export
        g = QGroupBox(t.t("export"))
        gl = QVBoxLayout(g)
        gl.setSpacing(6)
        row = QHBoxLayout()
        row.addWidget(QLabel(t.t("format") + ":"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.setMinimumHeight(36)
        self.fmt_combo.addItems(["mp3", "wav"])
        self.fmt_combo.setToolTip(t.t("tooltip_format"))
        row.addWidget(self.fmt_combo)
        gl.addLayout(row)
        self.export_btn = QPushButton(t.t("synthesize"))
        self.export_btn.setMinimumHeight(44)
        self.export_btn.setToolTip(t.t("tooltip_synthesize"))
        self.export_btn.clicked.connect(self._on_export)
        gl.addWidget(self.export_btn)
        self.save_btn = QPushButton(t.t("save_as"))
        self.save_btn.setMinimumHeight(44)
        self.save_btn.setToolTip(t.t("tooltip_save"))
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save_as)
        gl.addWidget(self.save_btn)
        layout.addWidget(g)
        
        # Progress
        g = QGroupBox(t.t("progress"))
        gl = QVBoxLayout(g)
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setToolTip(t.t("tooltip_progress"))
        gl.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setToolTip(t.t("tooltip_progress"))
        gl.addWidget(self.progress_bar)
        row = QHBoxLayout()
        self.elapsed_label = QLabel(t.t("elapsed") + ": 00:00")
        self.elapsed_label.setToolTip(t.t("tooltip_elapsed"))
        self.total_label = QLabel(t.t("total") + ": 00:00")
        self.total_label.setToolTip(t.t("tooltip_total"))
        row.addWidget(self.elapsed_label)
        row.addWidget(self.total_label)
        gl.addLayout(row)
        layout.addWidget(g)
        
        # Settings
        g = QGroupBox(t.t("settings"))
        gl = QVBoxLayout(g)
        row = QHBoxLayout()
        row.addWidget(QLabel(t.t("theme") + ":"))
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumHeight(36)
        self.theme_combo.addItems([t.t("dark"), t.t("light")])
        self.theme_combo.setToolTip(t.t("tooltip_theme"))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        row.addWidget(self.theme_combo)
        gl.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(t.t("language") + ":"))
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumHeight(36)
        self.lang_combo.addItems(["Русский", "English"])
        self.lang_combo.setToolTip(t.t("tooltip_language"))
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        row.addWidget(self.lang_combo)
        gl.addLayout(row)
        layout.addWidget(g)
        
        layout.addStretch()
        return panel
    
    def _create_menu(self):
        t = self.translations
        mb = self.menuBar()
        
        fm = mb.addMenu(t.t("file_menu"))
        a = QAction(t.t("open"), self)
        a.setShortcut("Ctrl+O")
        a.triggered.connect(self._on_open)
        fm.addAction(a)
        a = QAction(t.t("save"), self)
        a.setShortcut("Ctrl+S")
        a.triggered.connect(self._on_save_text)
        fm.addAction(a)
        fm.addSeparator()
        a = QAction(t.t("exit"), self)
        a.triggered.connect(self.close)
        fm.addAction(a)
        
        em = mb.addMenu(t.t("edit_menu"))
        a = QAction(t.t("undo"), self)
        a.setShortcut("Ctrl+Z")
        a.triggered.connect(self.text_edit.undo)
        em.addAction(a)
        a = QAction(t.t("redo"), self)
        a.setShortcut("Ctrl+Y")
        a.triggered.connect(self.text_edit.redo)
        em.addAction(a)
        em.addSeparator()
        a = QAction(t.t("cut"), self)
        a.setShortcut("Ctrl+X")
        a.triggered.connect(self.text_edit.cut)
        em.addAction(a)
        a = QAction(t.t("copy"), self)
        a.setShortcut("Ctrl+C")
        a.triggered.connect(self.text_edit.copy)
        em.addAction(a)
        a = QAction(t.t("paste"), self)
        a.setShortcut("Ctrl+V")
        a.triggered.connect(self.text_edit.paste)
        em.addAction(a)
        em.addSeparator()
        a = QAction(t.t("select_all"), self)
        a.setShortcut("Ctrl+A")
        a.triggered.connect(self.text_edit.selectAll)
        em.addAction(a)
        
        hm = mb.addMenu(t.t("help"))
        a = QAction(t.t("about"), self)
        a.triggered.connect(self._on_about)
        hm.addAction(a)
    
    def _init_tts(self):
        try:
            from tts.engine import get_available_engines
            engines = get_available_engines()
            names = {"edge_tts": "Edge TTS (online)", "piper": "Piper TTS (offline)", "supertonic": "Supertonic 3 (offline)", "pyttsx3": "pyttsx3"}
            self.engine_combo.clear()
            for e in engines:
                self.engine_combo.addItem(names.get(e, e), e)
            self.tts_engine = create_engine("auto")
            if self.tts_engine.initialize():
                self._populate_voices()
        except Exception as e:
            self.status_bar.showMessage(f"TTS error: {e}")
    
    def _ensure_edge_consent(self) -> bool:
        """Ensure Edge TTS cloud consent; disable Edge if declined."""
        from tts.edge_tts_wrapper import check_edge_consent
        if check_edge_consent(self.config, self):
            return True
        self.status_bar.showMessage("Edge TTS отключён: нет согласия на передачу данных")
        # Revert combo to a non-cloud engine if possible.
        for i in range(self.engine_combo.count()):
            if self.engine_combo.itemData(i) != "edge_tts":
                self.engine_combo.setCurrentIndex(i)
                break
        return False

    def _on_engine_changed(self, index):
        name = self.engine_combo.currentData()
        if not name:
            return
        if name == "edge_tts" and self.config.edge_consent != "accepted":
            if not self._ensure_edge_consent():
                return
        try:
            if self.playback_manager and self.playback_manager.is_playing:
                self.playback_manager.stop()
            self.tts_engine = create_engine(name)
            self.config.last_engine = name
            
            # Show download dialog for Supertonic if needed
            if name == "supertonic":
                from tts.supertonic_wrapper import is_supertonic_downloaded
                if not is_supertonic_downloaded():
                    from ui.download_dialog import show_download_dialog
                    if not show_download_dialog(self.tts_engine, self):
                        self.status_bar.showMessage("Загрузка Supertonic отменена")
                        return
            
            if self.tts_engine.initialize():
                self._populate_voices()
                if self.playback_manager:
                    self.playback_manager.tts_engine = self.tts_engine
                if self.exporter:
                    self.exporter.tts_engine = self.tts_engine
        except Exception as e:
            self.status_bar.showMessage(f"Engine error: {e}")
    
    def _populate_voices(self):
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        for v in self.tts_engine.get_voices():
            # Mark offline voices that need download
            suffix = ""
            try:
                if self._current_engine_name() == "piper" and hasattr(self.tts_engine, "is_voice_downloaded"):
                    if not self.tts_engine.is_voice_downloaded(v.id):
                        suffix = "  ↓ скачать"
            except Exception:
                pass
            self.voice_combo.addItem(f"{v.name} ({v.language}){suffix}", v.id)
        saved = self.config.voice
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == saved:
                self.voice_combo.setCurrentIndex(i)
                break
        self.voice_combo.blockSignals(False)
        self._update_voice_status()
    
    def _init_playback(self):
        if not self.tts_engine:
            return
        self.playback_manager = PlaybackManager(self.tts_engine)
        self.playback_manager.playback_started.connect(self._on_play_started)
        self.playback_manager.playback_stopped.connect(self._on_play_stopped)
        self.playback_manager.playback_finished.connect(self._on_play_finished)
        self.playback_manager.position_changed.connect(self._on_position)
        self.playback_manager.progress_updated.connect(self._on_playback_progress)
        self.playback_manager.error_occurred.connect(self._on_error)
        
        self.exporter = AudioExporter(self.tts_engine)
        self.exporter.export_started.connect(self._on_export_started)
        self.exporter.export_progress.connect(self._on_export_progress)
        self.exporter.export_progress_text.connect(self._on_export_text)
        self.exporter.export_complete.connect(self._on_export_complete)
        self.exporter.export_error.connect(self._on_error)
    
    def _load_settings(self):
        try:
            g = self.config.get("window_geometry")
            if g:
                self.restoreGeometry(g)
        except Exception:
            pass
        self.theme_combo.setCurrentIndex(0 if self.config.theme == "dark" else 1)
        self.lang_combo.setCurrentIndex(0 if self.config.language == "ru" else 1)
        try:
            saved_engine = self.config.last_engine or self.config.engine
            for i in range(self.engine_combo.count()):
                if self.engine_combo.itemData(i) == saved_engine:
                    self.engine_combo.setCurrentIndex(i)
                    break
        except Exception:
            pass
    
    def _load_default_text(self):
        """Load README.md into editor if empty (pet-project requirement #3)."""
        try:
            if self.text_edit.toPlainText().strip():
                return
            # Try frozen bundle first (dist/_internal or exe dir), then project root
            candidates = []
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                candidates.append(Path(sys._MEIPASS) / "README.md")
                candidates.append(Path(sys.executable).parent / "README.md")
                candidates.append(Path(sys.executable).parent / "_internal" / "README.md")
            candidates.append(Path(__file__).parent.parent / "README.md")
            for p in candidates:
                if p.is_file():
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    # Use first ~8k chars to avoid huge initial text
                    if len(text) > 8000:
                        text = text[:8000].rsplit("\n", 1)[0]
                    self.text_edit.setPlainText(text)
                    self._current_file = "README"
                    self._update_stats()
                    return
            # Fallback demo text if README not found
            self.text_edit.setPlainText("Привет! Это TTS Lite. Вставь свой текст сюда и нажми Play.\n\nHello! This is TTS Lite. Paste your text here and press Play.")
            self._update_stats()
        except Exception:
            pass

    def _update_voice_status(self):
        """Show 'need download' hint for offline voices and block playback."""
        try:
            engine_name = self._current_engine_name()
            voice_id = self.voice_combo.currentData()
            if not voice_id:
                self.voice_status_label.setText("")
                return
            if engine_name == "piper":
                try:
                    from tts.piper_wrapper import PiperEngine
                    # Use engine instance check if it has the method
                    is_dl = getattr(self.tts_engine, "is_voice_downloaded", None)
                    if callable(is_dl):
                        downloaded = is_dl(voice_id)
                    else:
                        downloaded = False
                    if not downloaded:
                        self.voice_status_label.setText("⚠ Голос не скачан — будет загружен при первом воспроизведении (~50 МБ)")
                        self.play_btn.setEnabled(False)
                        self.preview_btn.setEnabled(False)
                        self.export_btn.setEnabled(False)
                        return
                except Exception:
                    pass
            elif engine_name == "supertonic":
                try:
                    from tts.supertonic_wrapper import is_supertonic_downloaded
                    if not is_supertonic_downloaded():
                        self.voice_status_label.setText("⚠ Модель Supertonic не скачана — загрузка ~400 МБ при выборе движка")
                        return
                except Exception:
                    pass
            self.voice_status_label.setText("✓ Голос готов")
            self.play_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
        except Exception:
            self.voice_status_label.setText("")

    def _ensure_voice_downloaded(self, voice_id: str) -> bool:
        """Ensure offline voice is downloaded, showing progress dialog. Returns True if ready."""
        engine_name = self._current_engine_name()
        if engine_name == "piper":
            try:
                is_dl = getattr(self.tts_engine, "is_voice_downloaded", None)
                if callable(is_dl) and is_dl(voice_id):
                    return True
                # Show progress dialog for Piper voice
                from PySide6.QtWidgets import QProgressDialog
                from PySide6.QtCore import Qt as QtCore

                dlg = QProgressDialog(f"Загрузка голоса {voice_id}...", "Отмена", 0, 100, self)
                dlg.setWindowTitle("Загрузка голоса Piper")
                dlg.setWindowModality(QtCore.WindowModality.WindowModal)
                dlg.setAutoClose(False)
                dlg.setAutoReset(False)
                dlg.setValue(0)
                dlg.show()

                ok = {"value": False, "cancelled": False}

                def progress(p):
                    # p is 0..1
                    try:
                        if dlg.wasCanceled():
                            ok["cancelled"] = True
                            return
                        dlg.setValue(int(p * 100))
                    except Exception:
                        pass

                # Run download in worker thread to keep UI responsive
                import threading
                result = {"success": False}

                def do_download():
                    try:
                        result["success"] = bool(self.tts_engine.download_voice(voice_id, progress_callback=progress))
                    except Exception:
                        result["success"] = False

                th = threading.Thread(target=do_download, daemon=True)
                th.start()
                # Pump events while downloading
                while th.is_alive():
                    QApplication.processEvents()
                    time.sleep(0.05)
                    if dlg.wasCanceled():
                        break
                dlg.close()
                if result["success"] and not dlg.wasCanceled():
                    self.status_bar.showMessage(f"Голос {voice_id} загружен")
                    self._update_voice_status()
                    return True
                else:
                    self.status_bar.showMessage("Загрузка отменена или не удалась")
                    QMessageBox.warning(self, "Загрузка", f"Не удалось загрузить голос {voice_id}. Проверь интернет.")
                    return False
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки голоса: {e}")
                return False
        elif engine_name == "supertonic":
            try:
                from tts.supertonic_wrapper import is_supertonic_downloaded, show_download_dialog_if_needed
                if is_supertonic_downloaded():
                    return True
                from ui.download_dialog import show_download_dialog
                return bool(show_download_dialog(self.tts_engine, self))
            except Exception:
                return True
        return True

    def _save_settings(self):
        self.config.set("window_geometry", self.saveGeometry())
        self.config.save()
    
    def _current_engine_name(self):
        try:
            return self.engine_combo.currentData()
        except Exception:
            return None

    def _require_edge_consent_for_playback(self) -> bool:
        if self._current_engine_name() == "edge_tts":
            return self._ensure_edge_consent()
        return True

    # File
    def _on_open(self):
        fp, _ = QFileDialog.getOpenFileName(self, self.translations.t("open"), self.config.last_directory, get_file_filter())
        if fp:
            try:
                self.text_edit.setPlainText(load_file(fp))
                self.config.last_directory = str(Path(fp).parent)
                from utils.security import sanitize_filename
                self._current_file = sanitize_filename(Path(fp).stem)
                self._update_stats()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _on_save_text(self):
        from utils.security import sanitize_filename
        fp, _ = QFileDialog.getSaveFileName(self, self.translations.t("save"), self.config.last_directory, "Text Files (*.txt);;All Files (*)")
        if fp:
            try:
                path = Path(fp)
                if path.suffix.lower() not in (".txt", ""):
                    raise ValueError(f"Unsupported text format: {path.suffix!r}")
                if not path.suffix:
                    path = path.with_suffix(".txt")
                path.parent.mkdir(parents=True, exist_ok=True)
                # Sanitize only the file name, keep the chosen directory.
                safe = sanitize_filename(path.stem) + path.suffix.lower()
                path = path.parent / safe
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                self.config.last_directory = str(path.parent)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
    
    # Playback
    def _on_play(self):
        if not self._require_edge_consent_for_playback():
            return
        vid = self.voice_combo.currentData()
        if vid and not self._ensure_voice_downloaded(vid):
            return
        if self.playback_manager.is_playing:
            self.playback_manager._stop_event.set()
            if self.tts_engine and hasattr(self.tts_engine, 'stop'):
                self.tts_engine.stop()
            self.playback_manager.stop()
        
        text = self.text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, self.translations.t("warning"), self.translations.t("no_text"))
            return
        
        sentences = split_into_sentences(text)
        
        self.playback_manager.set_sentences(sentences)
        self.playback_manager.set_voice(self.voice_combo.currentData())
        self.playback_manager.set_volume(self.config.volume / 100)
        self.playback_manager.set_speed(self.config.speed)
        self.playback_manager.set_pitch(self.config.pitch)
        
        self._export_start_time = time.time()
        self.total_label.setText(f"{self.translations.t('total')}: --:--")
        
        self.playback_manager.play(0)
    
    def _on_stop(self):
        if self.playback_manager:
            # Set stop signal FIRST — so synthesis thread sees it before exception
            self.playback_manager._stop_event.set()
            if self.tts_engine and hasattr(self.tts_engine, 'stop'):
                self.tts_engine.stop()
            self.playback_manager.stop()
    
    def _on_preview(self):
        if not self.tts_engine:
            return
        if not self._require_edge_consent_for_playback():
            return
        vid = self.voice_combo.currentData()
        if vid and not self._ensure_voice_downloaded(vid):
            return
        if self.playback_manager.is_playing:
            self.playback_manager._stop_event.set()
            if self.tts_engine and hasattr(self.tts_engine, 'stop'):
                self.tts_engine.stop()
            self.playback_manager.stop()
        
        text = self.text_edit.textCursor().selectedText()
        if not text:
            QMessageBox.warning(self, self.translations.t("warning"), self.translations.t("select_text"))
            return
        
        text = text.replace('\u2029', ' ').replace('\u000b', ' ').replace('\r\n', ' ').replace('\r', ' ')
        text = ''.join(c for c in text if c.isprintable() or c in ' \n\t')
        text = ' '.join(text.split())
        
        if len(text) > 200:
            words = text[:200].rsplit(' ', 1)[0]
            text = words
        
        self.playback_manager.set_sentences([text])
        self.playback_manager.set_voice(self.voice_combo.currentData())
        self.playback_manager.set_volume(self.config.volume / 100)
        self.playback_manager.set_speed(self.config.speed)
        self.playback_manager.set_pitch(self.config.pitch)
        
        self.playback_manager.play(0)
    
    # Settings
    def _on_vol_changed(self, v):
        self.config.volume = v
        self.vol_label.setText(f"{v}%")
        if self.playback_manager:
            self.playback_manager.set_volume(v / 100)
    
    def _on_spd_changed(self, v):
        s = v / 100
        self.config.speed = s
        self.spd_label.setText(f"{s:.2f}x")
        if self.playback_manager:
            self.playback_manager.set_speed(s)
    
    def _on_pitch_changed(self, v):
        p = v / 100
        self.config.pitch = p
        self.pitch_label.setText(f"{p:.2f}x")
        if self.playback_manager:
            self.playback_manager.set_pitch(p)
    
    def _on_voice_changed(self, i):
        vid = self.voice_combo.currentData()
        if vid:
            self.config.voice = vid
            self.config.last_voice = vid
        self._update_voice_status()
    
    def _on_theme_changed(self, i):
        self.config.theme = "dark" if i == 0 else "light"
        apply_theme(QApplication.instance(), self.config.theme)
    
    def _on_lang_changed(self, i):
        lang = "ru" if i == 0 else "en"
        if lang == self.config.language:
            return
        r = QMessageBox.question(self, self.translations.t("restart_title"), self.translations.t("restart_text"),
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.config.language = lang
            self.config.save()
            subprocess.Popen([sys.executable] + sys.argv)
            QApplication.quit()
        else:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(0 if self.config.language == "ru" else 1)
            self.lang_combo.blockSignals(False)
    
    def _on_about(self):
        QMessageBox.about(self, self.translations.t("about"), 
            f"<h3>Text-to-Speech</h3><p>Version: {APP_VERSION}</p><p>cryptomonstrik@gmail.com</p>")
    
    # Timer
    def _start_timer(self):
        self._elapsed_seconds = 0
        self.elapsed_label.setText(f"{self.translations.t('elapsed')}: 00:00")
        self._elapsed_timer.start(1000)
    
    def _stop_timer(self):
        self._elapsed_timer.stop()
    
    def _tick_elapsed(self):
        self._elapsed_seconds += 1
        m = self._elapsed_seconds // 60
        s = self._elapsed_seconds % 60
        self.elapsed_label.setText(f"{self.translations.t('elapsed')}: {m:02d}:{s:02d}")
    
    # Callbacks
    def _on_play_started(self):
        self.status_bar.showMessage("Playing...")
        self._start_timer()
    
    def _on_play_stopped(self):
        self._stop_timer()
        self.progress_bar.setValue(0)
        self.elapsed_label.setText(f"{self.translations.t('elapsed')}: 00:00")
        self.status_bar.showMessage(self.translations.t("ready"))
    
    def _on_play_finished(self):
        self._stop_timer()
        self.progress_bar.setValue(100)
        self.status_bar.showMessage(self.translations.t("ready"))
    
    def _on_playback_progress(self, p):
        if p > 0 and self._export_start_time > 0:
            elapsed = time.time() - self._export_start_time
            total_est = elapsed / p
            m = int(total_est) // 60
            s = int(total_est) % 60
            self.total_label.setText(f"{self.translations.t('total')}: {m:02d}:{s:02d}")
    
    def _on_position(self, pos):
        pass
    
    def _on_export_started(self):
        self.status_bar.showMessage("Exporting...")
        self._start_timer()
    
    def _on_export_progress(self, p):
        self.progress_bar.setValue(int(p * 100))
        if p > 0 and self._export_start_time > 0:
            elapsed = time.time() - self._export_start_time
            total_est = elapsed / p
            m = int(total_est) // 60
            s = int(total_est) % 60
            self.total_label.setText(f"{self.translations.t('total')}: {m:02d}:{s:02d}")
    
    def _on_export_text(self, txt):
        self.progress_label.setText(txt)
        self.status_bar.showMessage(txt)
    
    def _on_export_complete(self, fp):
        self._stop_timer()
        self.progress_bar.setValue(100)
        self.progress_label.setText(self.translations.t("export_done"))
        self.export_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        QMessageBox.information(self, self.translations.t("info"), f"{self.translations.t('export_done')}\n{fp}")
    
    def _on_error(self, err):
        self._stop_timer()
        self.progress_bar.setValue(0)
        self.export_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        QMessageBox.critical(self, self.translations.t("error"), err)
    
    def _on_export(self):
        if not self.tts_engine:
            return
        if not self._require_edge_consent_for_playback():
            return
        vid = self.voice_combo.currentData()
        if vid and not self._ensure_voice_downloaded(vid):
            return
        text = self.text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, self.translations.t("warning"), self.translations.t("no_text"))
            return
        vid = self.voice_combo.currentData()
        if not vid:
            return
        
        fmt = self.fmt_combo.currentText()
        tmp = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False, prefix="tts_")
        self._temp_audio_path = tmp.name
        tmp.close()
        
        self.export_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self._export_start_time = time.time()
        self.total_label.setText(f"{self.translations.t('total')}: --:--")
        
        self.exporter.export_to_file(split_into_sentences(text), vid, self._temp_audio_path, fmt, self.config.speed, self.config.pitch)
    
    def _on_save_as(self):
        if not self._temp_audio_path or not os.path.exists(self._temp_audio_path):
            return
        fmt = self.fmt_combo.currentText()
        
        # Generate filename: textname_engine_voice_datetime (sanitized).
        from datetime import datetime
        from utils.security import sanitize_filename
        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        text_name = sanitize_filename(self._current_file or "tts")

        engine_name = sanitize_filename(self.engine_combo.currentData() or "tts")

        voice_id = self.voice_combo.currentData() or "voice"
        voice_name = sanitize_filename(str(voice_id).replace("-", "_").replace(" ", "_"))

        filename = f"{text_name}_{engine_name}_{voice_name}_{now}.{fmt}"
        
        fp, _ = QFileDialog.getSaveFileName(self, self.translations.t("save_as"), 
            os.path.join(self._music_folder, filename), f"Audio Files (*.{fmt})")
        if fp:
            import shutil
            shutil.copy2(self._temp_audio_path, fp)
            QMessageBox.information(self, self.translations.t("info"), f"{self.translations.t('saved')}\n{fp}")
    
    def _update_stats(self):
        text = self.text_edit.toPlainText()
        s = get_text_statistics(text)
        t = self.translations
        self.stats_label.setText(f"{s['sentences']} {t.t('sentences')}, {s['words']} {t.t('words')}, {s['characters']} {t.t('chars')}")
    
    def _update_preview_btn(self):
        t = self.translations
        self.preview_btn.setText(f"{t.t('preview')} (200)")
    
    def closeEvent(self, event):
        try:
            if self.playback_manager and self.playback_manager.is_playing:
                self.playback_manager.stop()
        except Exception:
            pass
        try:
            if self.exporter and self.exporter.is_exporting:
                self.exporter.cancel_export()
        except Exception:
            pass
        # Release TTS resources (stop Edge subprocess if running).
        try:
            if self.tts_engine and hasattr(self.tts_engine, 'stop'):
                self.tts_engine.stop()
        except Exception:
            pass
        if self._temp_audio_path and os.path.exists(self._temp_audio_path):
            try:
                os.unlink(self._temp_audio_path)
            except OSError:
                pass
        self._save_settings()
        event.accept()
