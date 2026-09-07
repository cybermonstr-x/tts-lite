"""Audio export functionality."""
import io
import os
import warnings
import tempfile
import numpy as np
import wave
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread

# Set ffmpeg path before pydub is imported to suppress warning
try:
    import imageio_ffmpeg
    os.environ["FFMPEG_BINARY"] = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    pass

# Suppress pydub ffmpeg warning
warnings.filterwarnings("ignore", message=".*ffmpeg.*", category=RuntimeWarning)

def _get_ffmpeg_path():
    """Get ffmpeg path, trying imageio_ffmpeg first."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    return "ffmpeg"

def _configure_pydub():
    """Configure pydub to use bundled ffmpeg."""
    try:
        ffmpeg_path = _get_ffmpeg_path()
        if ffmpeg_path:
            import pydub
            pydub.AudioSegment.converter = ffmpeg_path
            os.environ["FFMPEG_BINARY"] = ffmpeg_path
    except Exception:
        pass

class ExportWorker(QThread):
    """Worker thread for audio export."""
    
    progress_updated = Signal(float)
    progress_text = Signal(str)
    export_complete = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, tts_engine, sentences, voice_id, output_path, 
                 format_type, speed, pitch, parent=None):
        super().__init__(parent)
        self.tts_engine = tts_engine
        self.sentences = sentences
        self.voice_id = voice_id
        self.output_path = output_path
        self.format_type = format_type
        self.speed = speed
        self.pitch = pitch
        self._is_cancelled = False
    
    def run(self):
        """Perform export."""
        from utils.security import validate_export_path, validate_synthesis_text

        try:
            _configure_pydub()

            # Validate destination early (fail fast, no wasted synthesis).
            validated = validate_export_path(self.output_path, self.format_type)
            self.output_path = str(validated)

            all_audio = []
            sample_rate = None
            total_sentences = len(self.sentences)
            if total_sentences == 0:
                raise ValueError("No text to export")

            for i, sentence in enumerate(self.sentences):
                if self._is_cancelled:
                    return

                self.progress_text.emit(f"Synthesizing {i+1}/{total_sentences}...")

                try:
                    validate_synthesis_text(sentence)
                except ValueError:
                    continue  # skip empty sentences

                result = self.tts_engine.synthesize(
                    sentence, self.voice_id,
                    self.speed, self.pitch
                )
                if result is None:
                    # Synthesis was stopped/cancelled.
                    return
                audio, sr = result
                all_audio.append(audio)
                sample_rate = sr

                progress = (i + 1) / total_sentences
                self.progress_updated.emit(progress)

            if self._is_cancelled:
                return

            if not all_audio:
                raise ValueError("No audio generated (empty input?)")

            self.progress_text.emit("Saving file...")

            audio = np.concatenate(all_audio)
            
            if self.format_type == 'wav':
                self._save_wav(audio, sample_rate)
            elif self.format_type == 'mp3':
                self._save_mp3(audio, sample_rate)
            else:
                raise ValueError(f"Unsupported format: {self.format_type}")
            
            self.progress_updated.emit(1.0)
            self.export_complete.emit(str(self.output_path))
            
        except Exception as e:
            self.error_occurred.emit(f"Export error: {e}")
    
    def _save_wav(self, audio: np.ndarray, sample_rate: int):
        """Save audio as WAV file."""
        audio_int = (audio * 32767).astype(np.int16)
        
        with wave.open(str(self.output_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int.tobytes())
    
    def _save_mp3(self, audio: np.ndarray, sample_rate: int):
        """Save audio as MP3 file."""
        try:
            from pydub import AudioSegment
            
            audio_int = (audio * 32767).astype(np.int16)
            
            audio_segment = AudioSegment(
                audio_int.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=1
            )
            
            audio_segment.export(
                str(self.output_path),
                format="mp3",
                bitrate="192k"
            )
        except ImportError:
            self.progress_text.emit("pydub not installed, saving as WAV...")
            wav_path = str(self.output_path)
            if wav_path.lower().endswith('.mp3'):
                wav_path = wav_path[:-4] + '.wav'
            self.output_path = wav_path
            self._save_wav(audio, sample_rate)
        except Exception as e:
            self.progress_text.emit(f"MP3 error: {e}. Saving as WAV...")
            wav_path = str(self.output_path)
            if wav_path.lower().endswith('.mp3'):
                wav_path = wav_path[:-4] + '.wav'
            self.output_path = wav_path
            self._save_wav(audio, sample_rate)
    
    def cancel(self):
        """Cancel export."""
        self._is_cancelled = True

class AudioExporter(QObject):
    """Manages audio export operations."""
    
    export_started = Signal()
    export_progress = Signal(float)
    export_progress_text = Signal(str)
    export_complete = Signal(str)
    export_error = Signal(str)
    
    def __init__(self, tts_engine, parent=None):
        super().__init__(parent)
        self.tts_engine = tts_engine
        self._worker = None
        self._last_output_path = None
    
    def export_to_file(self, sentences: list, voice_id: str, output_path: str,
                       format_type: str = 'mp3', speed: float = 1.0,
                       pitch: float = 1.0):
        """Export sentences to audio file."""
        if self._worker and self._worker.isRunning():
            self.export_error.emit("Export already in progress")
            return

        if not sentences:
            self.export_error.emit("No text to export")
            return

        if format_type not in ('mp3', 'wav'):
            self.export_error.emit(f"Unsupported format: {format_type}")
            return

        if not voice_id:
            self.export_error.emit("No voice selected")
            return

        try:
            from utils.security import validate_export_path
            validated = validate_export_path(output_path, format_type)
            output_path = str(validated)
        except (ValueError, FileNotFoundError) as e:
            self.export_error.emit(str(e))
            return
        
        self._worker = ExportWorker(
            self.tts_engine,
            sentences,
            voice_id,
            output_path,
            format_type,
            speed,
            pitch
        )
        
        self._worker.progress_updated.connect(self.export_progress.emit)
        self._worker.progress_text.connect(self.export_progress_text.emit)
        self._worker.export_complete.connect(self._on_export_complete)
        self._worker.error_occurred.connect(self.export_error.emit)
        
        self._last_output_path = output_path
        self.export_started.emit()
        self._worker.start()
    
    def _on_export_complete(self, filepath: str):
        """Handle export completion."""
        self._last_output_path = filepath
        self.export_complete.emit(filepath)
    
    def cancel_export(self):
        """Cancel current export."""
        if self._worker:
            self._worker.cancel()
            self._worker.wait()
            self._worker = None
    
    @property
    def is_exporting(self):
        return self._worker is not None and self._worker.isRunning()
    
    @property
    def last_output_path(self):
        return self._last_output_path
