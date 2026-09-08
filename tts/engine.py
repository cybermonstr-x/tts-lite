"""TTS engine abstraction layer."""

import io
from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass

import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VoiceInfo:
    """Information about a TTS voice."""

    id: str
    name: str
    language: str
    gender: str  # "male" or "female"
    sample_rate: int = 22050


class TTSEngine(ABC):
    """Abstract base class for TTS engines."""

    def __init__(self):
        self.stop_event = None  # Set by PlaybackManager to allow interruption

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the TTS engine. Returns True if successful."""

    @abstractmethod
    def get_voices(self) -> list[VoiceInfo]:
        """Get list of available voices."""

    @abstractmethod
    def synthesize(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ) -> tuple[np.ndarray, int]:
        """Synthesize text to audio.

        Returns:
            Tuple of (audio_data_numpy_array, sample_rate)
        """

    @abstractmethod
    def synthesize_streaming(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ) -> Generator[tuple[np.ndarray, int], None, None]:
        """Synthesize text to audio with streaming.

        Yields:
            Tuple of (audio_chunk_numpy_array, sample_rate)
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the engine is available."""

    @abstractmethod
    def download_voice(self, voice_id: str) -> bool:
        """Download a voice model if needed."""


class FallbackEngine(TTSEngine):
    """Fallback engine using pyttsx3 or Windows SAPI."""

    def __init__(self):
        super().__init__()
        self.engine = None
        self._voices = []

    def initialize(self) -> bool:
        try:
            import pyttsx3

            self.engine = pyttsx3.init()
            # Get available voices
            for voice in self.engine.getProperty("voices"):
                self._voices.append(
                    VoiceInfo(
                        id=voice.id,
                        name=voice.name,
                        language=voice.languages[0] if voice.languages else "unknown",
                        gender="male" if "male" in voice.name.lower() else "female",
                    )
                )
            return True
        except Exception as e:
            logger.error("Failed to initialize pyttsx3: %s", e)
            return False

    def get_voices(self) -> list[VoiceInfo]:
        return self._voices

    def synthesize(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ) -> tuple[np.ndarray, int]:
        if not self.engine:
            raise RuntimeError("Engine not initialized")

        # Set voice
        self.engine.setProperty("voice", voice_id)
        # Set rate (pyttsx3 uses words per minute, default ~200)
        self.engine.setProperty("rate", int(200 * speed))

        # Synthesize to buffer
        buffer = io.BytesIO()
        self.engine.save_to_file(text, buffer)
        self.engine.runAndWait()

        # Convert to numpy array
        buffer.seek(0)
        import wave

        with wave.open(buffer, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            sample_rate = wf.getframerate()

        return audio, sample_rate

    def synthesize_streaming(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ) -> Generator[tuple[np.ndarray, int], None, None]:
        # For fallback, synthesize entire text at once (no real streaming)
        yield self.synthesize(text, voice_id, speed, pitch)

    def is_available(self) -> bool:
        try:
            import pyttsx3  # noqa: F401

            return True
        except ImportError:
            return False

    def download_voice(self, voice_id: str) -> bool:
        # No download needed for pyttsx3
        return True


def get_available_engines() -> list[str]:
    """Get list of available TTS engines."""
    engines = []

    # Edge TTS (online, high quality)
    try:
        from .edge_tts_wrapper import EdgeTTSEngine

        if EdgeTTSEngine().is_available():
            engines.append("edge_tts")
    except ImportError:
        pass

    # Piper TTS (offline, local)
    try:
        from .piper_wrapper import PiperEngine

        if PiperEngine().is_available():
            engines.append("piper")
    except ImportError:
        pass

    # Supertonic 3 (offline, ONNX, 31 languages)
    try:
        from .supertonic_wrapper import SupertonicEngine

        if SupertonicEngine().is_available():
            engines.append("supertonic")
    except ImportError:
        pass

    # pyttsx3 (fallback)
    try:
        import pyttsx3  # noqa: F401

        engines.append("pyttsx3")
    except ImportError:
        pass

    return engines


def create_engine(engine_name: str = "auto") -> TTSEngine:
    """Create a TTS engine instance."""
    if engine_name == "auto":
        # Try edge_tts first (better quality), then piper, then supertonic, then fallback
        try:
            from .edge_tts_wrapper import EdgeTTSEngine

            engine = EdgeTTSEngine()
            if engine.is_available():
                return engine
        except ImportError:
            pass

        try:
            from .piper_wrapper import PiperEngine

            engine = PiperEngine()
            if engine.is_available():
                return engine
        except ImportError:
            pass

        try:
            from .supertonic_wrapper import SupertonicEngine

            engine = SupertonicEngine()
            if engine.is_available():
                return engine
        except ImportError:
            pass

        return FallbackEngine()

    elif engine_name == "edge_tts":
        from .edge_tts_wrapper import EdgeTTSEngine

        return EdgeTTSEngine()

    elif engine_name == "piper":
        from .piper_wrapper import PiperEngine

        return PiperEngine()

    elif engine_name == "supertonic":
        from .supertonic_wrapper import SupertonicEngine

        return SupertonicEngine()

    elif engine_name == "pyttsx3":
        return FallbackEngine()

    else:
        raise ValueError(f"Unknown engine: {engine_name}")
