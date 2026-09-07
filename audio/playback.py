"""Audio playback manager with streaming support."""
import time
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, QThread
import threading
import queue

class PlaybackWorker(QThread):
    """Worker thread for audio playback."""
    
    position_changed = Signal(float)
    playback_finished = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, audio_queue: queue.Queue, sample_rate: int):
        super().__init__()
        self.audio_queue = audio_queue
        self.sample_rate = sample_rate
        self._is_playing = False
        self._should_stop = False
        self._volume = 1.0
        self._current_position = 0.0
        self._buffer = np.array([], dtype=np.float32)
        self._buffer_lock = threading.Lock()
        self.finished_event = threading.Event()
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """Callback for sounddevice - fills output buffer."""
        if self._should_stop or not self._is_playing:
            outdata[:] = np.zeros((frames, 1), dtype=np.float32)
            return
        
        with self._buffer_lock:
            if len(self._buffer) >= frames:
                outdata[:, 0] = self._buffer[:frames] * self._volume
                self._buffer = self._buffer[frames:]
            elif len(self._buffer) > 0:
                outdata[:len(self._buffer), 0] = self._buffer * self._volume
                outdata[len(self._buffer):, 0] = np.zeros(frames - len(self._buffer), dtype=np.float32)
                self._buffer = np.array([], dtype=np.float32)
            else:
                outdata[:] = np.zeros((frames, 1), dtype=np.float32)
        
        self._current_position += frames / self.sample_rate
        self.position_changed.emit(self._current_position)
    
    def run(self):
        self._stream = None
        try:
            self._is_playing = True
            
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=0,
                callback=self._audio_callback
            )
            self._stream.start()
            
            total_chunks = 0
            while not self._should_stop:
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.05)
                    
                    if audio_chunk is None:
                        break
                    
                    if self._should_stop:
                        break
                    
                    # NOTE: volume is applied once in _audio_callback.
                    # Do NOT scale here to avoid double (squared) attenuation.
                    audio_chunk = np.asarray(audio_chunk, dtype=np.float32)

                    with self._buffer_lock:
                        self._buffer = np.concatenate([self._buffer, audio_chunk])
                    
                    total_chunks += 1
                
                except queue.Empty:
                    continue
                except Exception as e:
                    if not self._should_stop:
                        self.error_occurred.emit(str(e))
                    break
            
            # Wait for buffer to drain — динамически по длине буфера
            if not self._should_stop:
                with self._buffer_lock:
                    remaining = len(self._buffer) / self.sample_rate if len(self._buffer) > 0 else 0
                deadline = time.time() + remaining + 5.0
                while time.time() < deadline:
                    with self._buffer_lock:
                        if len(self._buffer) == 0:
                            break
                    time.sleep(0.01)
            
            self._is_playing = False
            if not self._should_stop:
                self.playback_finished.emit()
                
        except Exception as e:
            if not self._should_stop:
                self.error_occurred.emit(str(e))
            self._is_playing = False
        finally:
            self.finished_event.set()
            try:
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
            except Exception:
                pass
    
    def stop(self):
        self._should_stop = True
        self._is_playing = False
        with self._buffer_lock:
            self._buffer = np.array([], dtype=np.float32)
        # Force close the audio stream
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
        # Wait for the thread to finish (finally block sets finished_event)
        self.finished_event.wait(timeout=5.0)
    
    @property
    def is_playing(self):
        return self._is_playing
    
    @property
    def position(self):
        return self._current_position

class PlaybackManager(QObject):
    """Manages audio playback and TTS integration."""
    
    playback_started = Signal()
    playback_stopped = Signal()
    playback_finished = Signal()
    position_changed = Signal(float)
    progress_updated = Signal(float)
    error_occurred = Signal(str)
    
    def __init__(self, tts_engine, parent=None):
        super().__init__(parent)
        self.tts_engine = tts_engine
        self._audio_queue = queue.Queue()
        self._worker = None
        self._sentences = []
        self._sentences_copy = []
        self._current_sentence_index = 0
        self._volume = 0.8
        self._speed = 1.0
        self._pitch = 1.0
        self._voice_id = None
        self._is_playing = False
        self._synthesis_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
    
    def set_sentences(self, sentences: list):
        with self._lock:
            self._sentences = sentences
            self._current_sentence_index = 0
    
    def set_voice(self, voice_id: str):
        self._voice_id = voice_id
    
    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))
        if self._worker:
            self._worker._volume = self._volume
    
    def set_speed(self, speed: float):
        self._speed = max(0.5, min(2.0, speed))
    
    def set_pitch(self, pitch: float):
        self._pitch = max(0.5, min(2.0, pitch))
    
    def play(self, start_index: int = 0):
        """Start playback from the specified sentence index."""
        with self._lock:
            if not self._sentences:
                self.error_occurred.emit("No sentences to play")
                return
            
            if not self._voice_id:
                self.error_occurred.emit("No voice selected")
                return
            
            # Clean up old playback WITHOUT emitting playback_stopped
            self._is_playing = False
            self._stop_event.set()
            if self.tts_engine:
                self.tts_engine.stop_event = None
            if self._worker:
                self._worker.stop()
                self._worker = None
            if self._synthesis_thread and self._synthesis_thread.is_alive():
                self._synthesis_thread.join(timeout=2.0)
            self._synthesis_thread = None
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Set up new playback
            self._sentences_copy = self._sentences.copy()
            self._current_sentence_index = start_index
            self._is_playing = True
            self._stop_event.clear()
        
        self._worker = PlaybackWorker(self._audio_queue, 22050)
        self._worker.position_changed.connect(self._on_position_changed)
        self._worker.playback_finished.connect(self._on_playback_finished)
        self._worker.error_occurred.connect(self._on_error)
        
        # Give engine access to stop_event so it can interrupt synthesis
        if self.tts_engine:
            self.tts_engine.stop_event = self._stop_event
        
        self._synthesis_thread = threading.Thread(
            target=self._synthesize_sentences,
            daemon=True
        )
        self._synthesis_thread.start()
        
        self._worker.start()
        self.playback_started.emit()
    
    def _synthesize_sentences(self):
        """Synthesize sentences and add to queue."""
        try:
            sentences_copy = self._sentences_copy.copy()
            total = len(sentences_copy)
            
            for i in range(self._current_sentence_index, total):
                if not self._is_playing or self._stop_event.is_set():
                    break
                
                if i >= len(sentences_copy):
                    break
                
                sentence = sentences_copy[i]
                
                if not sentence or not sentence.strip():
                    continue
                
                chunk_count = 0
                for audio_chunk, sample_rate in self.tts_engine.synthesize_streaming(
                    sentence, self._voice_id, self._speed, self._pitch
                ):
                    if not self._is_playing or self._stop_event.is_set():
                        break
                    self._audio_queue.put(audio_chunk)
                    chunk_count += 1
                
                if self._stop_event.is_set():
                    break
                
                self._current_sentence_index = i + 1
                
                progress = (i + 1) / total if total > 0 else 0
                self.progress_updated.emit(progress)
            
            if not self._stop_event.is_set():
                self._audio_queue.put(None)
                # Wait for worker to finish playing — 60с для длинного аудио
                if self._worker:
                    self._worker.finished_event.wait(timeout=60)
                # Signal completion
                self._is_playing = False
                self.playback_finished.emit()
            
        except Exception as e:
            if not self._stop_event.is_set():
                self.error_occurred.emit(f"Synthesis error: {e}")
                self._audio_queue.put(None)
    
    def stop(self):
        """Stop playback and synthesis. Non-blocking."""
        self._is_playing = False
        self._stop_event.set()
        self._current_sentence_index = 0
        
        # DON'T clear tts_engine.stop_event — synthesis thread needs it to exit
        
        # Stop monitor timer
        if hasattr(self, '_monitor_timer') and self._monitor_timer:
            self._monitor_timer.stop()
        
        # Stop worker (force-closes stream, waits for thread to finish — fast)
        if self._worker:
            self._worker.stop()
            self._worker = None
        
        # Don't join synthesis thread — it's daemon, will exit when stop_event is set
        # The engine's stop_event mechanism interrupts TTS immediately
        self._synthesis_thread = None
        
        # Drain audio queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        
        self.playback_stopped.emit()
    
    def preview_selection(self, text: str):
        """Preview a text selection."""
        if not text.strip():
            self.error_occurred.emit("No text to preview")
            return
        
        self.stop()
        
        from utils.text_processing import split_into_sentences
        with self._lock:
            self._sentences = split_into_sentences(text)
            self._current_sentence_index = 0
        
        self.play(0)
    
    def _on_position_changed(self, position: float):
        self.position_changed.emit(position)
    
    def _on_playback_finished(self):
        self._is_playing = False
        self.playback_finished.emit()
    
    def _on_error(self, error: str):
        self._is_playing = False
        self.error_occurred.emit(error)
    
    @property
    def is_playing(self):
        return self._is_playing
    
    @property
    def current_sentence_index(self):
        return self._current_sentence_index
    
    @property
    def total_sentences(self):
        return len(self._sentences)
