"""Piper TTS engine wrapper."""
import os
import io
from pathlib import Path
from typing import Optional, List, Generator, Tuple
import numpy as np
import wave
import struct

from .engine import TTSEngine, VoiceInfo

# Available Piper voices for download
AVAILABLE_VOICES = {
    "ru_RU-irina-medium": {
        "name": "Ирина (русский, женский)",
        "language": "ru",
        "gender": "female",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx.json"
    },
    "ru_RU-ruslan-medium": {
        "name": "Руслан (русский, мужской)",
        "language": "ru",
        "gender": "male",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx.json"
    },
    "en_US-lessac-medium": {
        "name": "Lessac (English, male)",
        "language": "en",
        "gender": "male",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
    },
    "en_US-amy-medium": {
        "name": "Amy (English, female)",
        "language": "en",
        "gender": "female",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
    },
}

class PiperEngine(TTSEngine):
    """Piper TTS engine wrapper."""
    
    def __init__(self):
        super().__init__()
        self._voices_dir = Path.home() / ".tts_app" / "voices"
        self._initialized = False
        self._model = None
        self._config = None
        self._current_voice = None
    
    def _ensure_voices_dir(self):
        """Create voices directory if it doesn't exist."""
        self._voices_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize(self) -> bool:
        """Initialize Piper TTS engine."""
        try:
            import piper
            self._ensure_voices_dir()
            self._initialized = True
            return True
        except ImportError:
            print("piper-tts not installed. Run: pip install piper-tts")
            return False
    
    def get_voices(self) -> List[VoiceInfo]:
        """Get list of available voices."""
        voices = []
        for voice_id, info in AVAILABLE_VOICES.items():
            voices.append(VoiceInfo(
                id=voice_id,
                name=info["name"],
                language=info["language"],
                gender=info["gender"]
            ))
        return voices
    
    def _get_voice_path(self, voice_id: str) -> Path:
        """Get path to voice model file."""
        return self._voices_dir / f"{voice_id}.onnx"
    
    def _get_config_path(self, voice_id: str) -> Path:
        """Get path to voice config file."""
        return self._voices_dir / f"{voice_id}.onnx.json"
    
    def is_voice_downloaded(self, voice_id: str) -> bool:
        """Check if voice model is downloaded."""
        return self._get_voice_path(voice_id).exists()
    
    def download_voice(self, voice_id: str, progress_callback=None) -> bool:
        """Download a voice model from Hugging Face."""
        if voice_id not in AVAILABLE_VOICES:
            print(f"Unknown voice: {voice_id}")
            return False
        
        if self.is_voice_downloaded(voice_id):
            return True
        
        try:
            import requests
            
            voice_info = AVAILABLE_VOICES[voice_id]
            
            # Download model file
            model_path = self._get_voice_path(voice_id)
            print(f"Downloading voice model: {voice_id}...")
            
            response = requests.get(voice_info["url"], stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded / total_size)
            
            # Download config file
            config_path = self._get_config_path(voice_id)
            response = requests.get(voice_info["config_url"])
            response.raise_for_status()
            
            with open(config_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Voice downloaded: {voice_id}")
            return True
            
        except Exception as e:
            print(f"Failed to download voice {voice_id}: {e}")
            # Clean up partial download
            model_path = self._get_voice_path(voice_id)
            if model_path.exists():
                model_path.unlink()
            return False
    
    def _load_model(self, voice_id: str):
        """Load Piper model for the specified voice."""
        try:
            import piper
            
            model_path = self._get_voice_path(voice_id)
            config_path = self._get_config_path(voice_id)
            
            if not model_path.exists():
                if not self.download_voice(voice_id):
                    raise RuntimeError(f"Failed to download voice: {voice_id}")
            
            # Load model
            self._model = piper.PiperVoice.load(model_path, config_path)
            self._current_voice = voice_id
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Piper model: {e}")
    
    def synthesize(self, text: str, voice_id: str, speed: float = 1.0,
                   pitch: float = 1.0) -> Tuple[np.ndarray, int]:
        """Synthesize text to audio."""
        if not self._initialized:
            raise RuntimeError("Engine not initialized")
        
        # Load model if needed
        if self._model is None or self._current_voice != voice_id:
            self._load_model(voice_id)
        
        # Synthesize
        audio_chunks = []
        sample_rate = self._model.config.sample_rate
        
        for chunk in self._model.synthesize(text):
            # Convert AudioChunk to numpy array
            audio_data = chunk.audio_int16_array.astype(np.float32) / 32768.0
            audio_chunks.append(audio_data)
        
        # Concatenate chunks
        audio = np.concatenate(audio_chunks)
        
        # Adjust speed by resampling
        if speed != 1.0:
            import scipy.signal
            new_length = int(len(audio) / speed)
            audio = scipy.signal.resample(audio, new_length).astype(np.float32)
        
        return audio, sample_rate
    
    def synthesize_streaming(self, text: str, voice_id: str, speed: float = 1.0,
                             pitch: float = 1.0) -> Generator[Tuple[np.ndarray, int], None, None]:
        """Synthesize text to audio with streaming."""
        if not self._initialized:
            raise RuntimeError("Engine not initialized")
        
        # Load model if needed
        if self._model is None or self._current_voice != voice_id:
            self._load_model(voice_id)
        
        sample_rate = self._model.config.sample_rate
        
        # Stream synthesis
        for chunk in self._model.synthesize(text):
            if self.stop_event and self.stop_event.is_set():
                return
            
            # Convert AudioChunk to numpy array
            audio = chunk.audio_int16_array.astype(np.float32) / 32768.0
            
            # Adjust speed
            if speed != 1.0:
                import scipy.signal
                new_length = int(len(audio) / speed)
                audio = scipy.signal.resample(audio, new_length).astype(np.float32)
            
            yield audio, sample_rate
    
    def is_available(self) -> bool:
        """Check if Piper is available."""
        try:
            import piper
            return True
        except ImportError:
            return False
