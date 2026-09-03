"""Supertonic 3 TTS engine wrapper."""
import os
import io
import wave
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Generator
import numpy as np

from .engine import TTSEngine, VoiceInfo


def is_supertonic_downloaded() -> bool:
    """Check if Supertonic model is already downloaded."""
    import os
    cache_path = os.path.expanduser("~/.cache/supertonic3")
    if os.path.exists(cache_path):
        # Check for model files
        onnx_path = os.path.join(cache_path, "onnx")
        if os.path.exists(onnx_path):
            return True
    return False


def show_download_dialog_if_needed(parent=None) -> bool:
    """Show download dialog if model is not cached. Returns True if ready."""
    if is_supertonic_downloaded():
        return True
    
    try:
        from ui.download_dialog import show_download_dialog
        from tts.engine import create_engine
        engine = create_engine("supertonic")
        return show_download_dialog(engine, parent)
    except ImportError:
        return True


class SupertonicEngine(TTSEngine):
    """Supertonic 3 TTS engine - lightweight ONNX-based TTS with 31 languages."""
    
    # Built-in voice styles with descriptive names
    VOICES = [
        VoiceInfo(id="M1", name="M1 — Мужской (четкий)", language="ru/en", gender="male"),
        VoiceInfo(id="M2", name="M2 — Мужской (спокойный)", language="ru/en", gender="male"),
        VoiceInfo(id="M3", name="M3 — Мужской (энергичный)", language="ru/en", gender="male"),
        VoiceInfo(id="M4", name="M4 — Мужской (глубокий)", language="ru/en", gender="male"),
        VoiceInfo(id="M5", name="M5 — Мужской (мягкий)", language="ru/en", gender="male"),
        VoiceInfo(id="F1", name="F1 — Женский (чёткий)", language="ru/en", gender="female"),
        VoiceInfo(id="F2", name="F2 — Женский (спокойный)", language="ru/en", gender="female"),
        VoiceInfo(id="F3", name="F3 — Женский (энергичный)", language="ru/en", gender="female"),
        VoiceInfo(id="F4", name="F4 — Женский (глубокий)", language="ru/en", gender="female"),
        VoiceInfo(id="F5", name="F5 — Женский (мягкий)", language="ru/en", gender="female"),
    ]
    
    def __init__(self):
        super().__init__()
        self._tts = None
        self._available = None
    
    def initialize(self) -> bool:
        """Initialize Supertonic TTS engine."""
        try:
            from supertonic import TTS
            self._tts = TTS(auto_download=True)
            return True
        except ImportError:
            print("Supertonic not installed. Run: pip install supertonic")
            return False
        except Exception as e:
            print(f"Failed to initialize Supertonic: {e}")
            return False
    
    def get_voices(self) -> List[VoiceInfo]:
        """Get list of available voices."""
        return self.VOICES
    
    def _get_lang_code(self, voice_id: str) -> str:
        """Map voice ID to language code (Supertonic uses 'na' for auto-detect)."""
        return "na"  # language-agnostic mode
    
    def synthesize(self, text: str, voice_id: str, speed: float = 1.0,
                   pitch: float = 1.0) -> Tuple[np.ndarray, int]:
        """Synthesize text to audio."""
        if not self._tts:
            raise RuntimeError("Supertonic engine not initialized")
        
        try:
            if self.stop_event and self.stop_event.is_set():
                return np.array([], dtype=np.float32), 22050
            
            style = self._tts.get_voice_style(voice_name=voice_id)
            
            # Supertonic speed range: 0.7 - 2.0, default 1.05
            supertonic_speed = max(0.7, min(2.0, speed))
            
            wav, duration = self._tts.synthesize(
                text=text,
                lang=self._get_lang_code(voice_id),
                voice_style=style,
                total_steps=8,
                speed=supertonic_speed,
            )
            
            # Convert wav bytes to numpy array
            audio, sample_rate = self._wav_to_numpy(wav)
            return audio, sample_rate
            
        except Exception as e:
            raise RuntimeError(f"Supertonic synthesis failed: {e}")
    
    def synthesize_streaming(self, text: str, voice_id: str, speed: float = 1.0,
                             pitch: float = 1.0) -> Generator[Tuple[np.ndarray, int], None, None]:
        """Synthesize text to audio with streaming (yields full audio as single chunk)."""
        yield self.synthesize(text, voice_id, speed, pitch)
    
    def _wav_to_numpy(self, wav_data) -> Tuple[np.ndarray, int]:
        """Convert Supertonic WAV output to numpy array, resampled to 22050 Hz."""
        import io
        from scipy.signal import resample
        
        TARGET_SR = 22050  # Match Edge TTS / Piper sample rate
        
        # Supertonic returns numpy array with shape (1, samples) as float32 at 44100 Hz
        if isinstance(wav_data, np.ndarray):
            # Flatten if 2D (shape (1, samples))
            if wav_data.ndim > 1:
                wav_data = wav_data.flatten()
            # Resample from 44100 to 22050
            original_sr = 44100
            if original_sr != TARGET_SR:
                num_samples = int(len(wav_data) * TARGET_SR / original_sr)
                wav_data = resample(wav_data, num_samples).astype(np.float32)
            return wav_data, TARGET_SR
        elif isinstance(wav_data, (str, Path)):
            with wave.open(str(wav_data), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                sample_rate = wf.getframerate()
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                if sample_rate != TARGET_SR:
                    num_samples = int(len(audio) * TARGET_SR / sample_rate)
                    audio = resample(audio, num_samples).astype(np.float32)
                return audio, TARGET_SR
        elif isinstance(wav_data, bytes):
            buf = io.BytesIO(wav_data)
            with wave.open(buf, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                sample_rate = wf.getframerate()
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                if sample_rate != TARGET_SR:
                    num_samples = int(len(audio) * TARGET_SR / sample_rate)
                    audio = resample(audio, num_samples).astype(np.float32)
                return audio, TARGET_SR
        else:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                self._tts.save_audio(wav_data, f.name)
                with wave.open(f.name, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    sample_rate = wf.getframerate()
                    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    if sample_rate != TARGET_SR:
                        num_samples = int(len(audio) * TARGET_SR / sample_rate)
                        audio = resample(audio, num_samples).astype(np.float32)
                os.unlink(f.name)
                return audio, TARGET_SR
    
    def is_available(self) -> bool:
        """Check if Supertonic is available."""
        if self._available is not None:
            return self._available
        
        try:
            import supertonic
            self._available = True
        except ImportError:
            self._available = False
        
        return self._available
    
    def download_voice(self, voice_id: str) -> bool:
        """Download voice model if needed (auto-downloaded on first use)."""
        return True
