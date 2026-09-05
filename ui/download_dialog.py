"""Download progress dialog for model loading."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from typing import Optional
import sys
import io


class RedirectOutput(io.StringIO):
    """Redirect stdout/stderr to capture progress messages."""
    
    def __init__(self, signal):
        super().__init__()
        self._signal = signal
        self._original = sys.stdout
    
    def write(self, text):
        if text.strip():
            self._signal.emit(text.strip())
        self._original.write(text)
    
    def flush(self):
        self._original.flush()


class DownloadWorker(QThread):
    """Worker thread for downloading model."""
    
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._is_error = False
    
    def run(self):
        try:
            self.progress.emit("Инициализация Supertonic 3...")
            self.progress.emit("Загрузка модели (~400 МБ)...")
            self.progress.emit("Это может занять 2-3 минуты при первом запуске")
            
            # Redirect stdout to capture download progress
            old_stdout = sys.stdout
            sys.stdout = RedirectOutput(self.progress)
            
            try:
                result = self.engine.initialize()
                sys.stdout = old_stdout
                
                if result:
                    self.progress.emit("Модель успешно загружена!")
                    self.finished.emit(True, "Supertonic 3 готов к работе")
                else:
                    self.finished.emit(False, "Не удалось инициализировать Supertonic")
            except Exception as e:
                sys.stdout = old_stdout
                raise e
                
        except Exception as e:
            self.finished.emit(False, f"Ошибка: {str(e)}")


class DownloadDialog(QDialog):
    """Dialog showing download progress."""
    
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.worker = None
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Загрузка Supertonic 3")
        self.setFixedSize(450, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Загрузка модели Supertonic 3")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info group
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()
        
        self.status_label = QLabel("Подготовка к загрузке...")
        self.status_label.setWordWrap(True)
        info_layout.addWidget(self.status_label)
        
        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("color: gray;")
        info_layout.addWidget(self.detail_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setEnabled(False)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
    
    def start_download(self):
        """Start the download process."""
        self.worker = DownloadWorker(self.engine)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
        
        self.cancel_btn.setEnabled(True)
        self.close_btn.setEnabled(False)
    
    def _on_progress(self, message: str):
        """Handle progress message."""
        self.status_label.setText(message)
        # Update detail with timestamp
        self.detail_label.setText(f"Получено: {message[:50]}...")
    
    def _on_finished(self, success: bool, message: str):
        """Handle download completion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)
        
        self.status_label.setText(message)
        self.detail_label.setText("Готово" if success else "Ошибка загрузки")
        
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        
        if success:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        else:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
    
    def _on_cancel(self):
        """Handle cancel button."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        
        self.status_label.setText("Загрузка отменена")
        self.detail_label.setText("")
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        event.accept()


def show_download_dialog(engine, parent=None) -> bool:
    """Show download dialog and return True if successful."""
    dialog = DownloadDialog(engine, parent)
    dialog.start_download()
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted
