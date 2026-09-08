"""Piper TTS engine wrapper (offline, models from Hugging Face over HTTPS)."""

import hashlib
import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import numpy as np

from utils.logger import get_logger, preview_text

from .engine import TTSEngine, VoiceInfo

logger = get_logger(__name__)

# All model URLs use HTTPS; SSL verification is always enabled (requests
# default ``verify=True`` is kept and made explicit).
# Models live under the per-user cache dir with owner-only permissions.
MODELS_DIR_NAME = ("tts_lite", "models", "piper")
DOWNLOAD_TIMEOUT = 90  # seconds per request (VPN-friendly, was 30)

# Available Piper voices for download.
# SHA-256 hashes guard integrity (audit §1.2). If a hash is None, the file
# is verified by size (>0 bytes) and the expected hash should be recorded
# after the first trusted download — see docs/SECURITY.md.
AVAILABLE_VOICES = {
    "ru_RU-irina-medium": {
        "name": "Ирина (русский, женский)",
        "language": "ru",
        "gender": "female",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx.json",  # noqa: E501
        "sha256": None,
    },
    "ru_RU-ruslan-medium": {
        "name": "Руслан (русский, мужской)",
        "language": "ru",
        "gender": "male",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx",  # noqa: E501
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx.json",  # noqa: E501
        "sha256": None,
    },
    "en_US-lessac-medium": {
        "name": "Lessac (English, male)",
        "language": "en",
        "gender": "male",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",  # noqa: E501
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",  # noqa: E501
        "sha256": None,
    },
    "en_US-amy-medium": {
        "name": "Amy (English, female)",
        "language": "en",
        "gender": "female",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json",  # noqa: E501
        "sha256": None,
    },
}


def get_models_dir() -> Path:
    """Return the secure per-user models directory (created with 0o700)."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        models_dir = base / "tts_lite" / "models" / "piper"
    else:
        models_dir = Path.home() / ".cache" / "tts-lite" / "models" / "piper"
    models_dir.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(models_dir, 0o700)
        except OSError:
            pass
    return models_dir


def sha256_of_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_voice_file(path: Path, expected_sha256: str | None) -> bool:
    """Verify a downloaded voice file: existence, non-empty, optional hash."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    if expected_sha256:
        actual = sha256_of_file(path)
        if actual.lower() != expected_sha256.lower():
            logger.error("SHA-256 mismatch for %s", path.name)
            return False
    return True


class PiperEngine(TTSEngine):
    """Piper TTS engine wrapper."""

    def __init__(self):
        super().__init__()
        self._voices_dir = get_models_dir()
        self._initialized = False
        self._model = None
        self._current_voice = None

    def _ensure_voices_dir(self):
        """Create voices directory if it doesn't exist."""
        self._voices_dir = get_models_dir()

    def initialize(self) -> bool:
        """Initialize Piper TTS engine."""
        try:
            import piper  # noqa: F401

            self._ensure_voices_dir()
            self._initialized = True
            return True
        except ImportError:
            logger.error("piper-tts not installed. Run: pip install piper-tts")
            return False

    def get_voices(self) -> list[VoiceInfo]:
        """Get list of available voices."""
        voices = []
        for voice_id, info in AVAILABLE_VOICES.items():
            voices.append(
                VoiceInfo(
                    id=voice_id,
                    name=info["name"],
                    language=info["language"],
                    gender=info["gender"],
                )
            )
        return voices

    def _get_voice_path(self, voice_id: str) -> Path:
        """Get path to voice model file."""
        safe_id = Path(voice_id).name
        return self._voices_dir / f"{safe_id}.onnx"

    def _get_config_path(self, voice_id: str) -> Path:
        """Get path to voice config file."""
        safe_id = Path(voice_id).name
        return self._voices_dir / f"{safe_id}.onnx.json"

    def is_voice_downloaded(self, voice_id: str) -> bool:
        """Check if voice model is downloaded and valid."""
        info = AVAILABLE_VOICES.get(voice_id)
        expected = info.get("sha256") if info else None
        return verify_voice_file(self._get_voice_path(voice_id), expected)

    def _download_url_to_file(self, url: str, dest: Path, progress_callback=None):
        """Download an HTTPS URL to dest atomically (temp file + rename)."""
        import requests

        if not url.startswith("https://"):
            raise RuntimeError(f"Refusing insecure download URL: {url}")

        # Atomic write: download to temp file in the same directory, then rename.
        tmp_fd, tmp_name = tempfile.mkstemp(dir=str(dest.parent), prefix=".dl_")
        os.close(tmp_fd)
        tmp_path = Path(tmp_name)
        try:
            # verify=True is the requests default; stated explicitly for the audit.
            with requests.get(
                url, stream=True, timeout=DOWNLOAD_TIMEOUT, verify=True
            ) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded / total_size)
            if tmp_path.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty")
            if os.name != "nt":
                try:
                    os.chmod(tmp_path, 0o600)
                except OSError:
                    pass
            tmp_path.replace(dest)
            if os.name != "nt":
                try:
                    os.chmod(dest, 0o600)
                except OSError:
                    pass
        finally:
            if tmp_path.exists() and tmp_path != dest:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def download_voice(self, voice_id: str, progress_callback=None) -> bool:
        """Download a voice model from Hugging Face (HTTPS, verified)."""
        if voice_id not in AVAILABLE_VOICES:
            logger.error("Unknown voice requested: %s", voice_id)
            return False

        if self.is_voice_downloaded(voice_id):
            return True

        try:
            import requests  # noqa: F401 — checked early for a clear error

            voice_info = AVAILABLE_VOICES[voice_id]
            model_path = self._get_voice_path(voice_id)
            logger.info("Downloading voice model: %s", voice_id)

            self._download_url_to_file(voice_info["url"], model_path, progress_callback)

            config_path = self._get_config_path(voice_id)
            self._download_url_to_file(voice_info["config_url"], config_path)

            if not verify_voice_file(model_path, voice_info.get("sha256")):
                raise RuntimeError("Downloaded model failed integrity check")
            if not config_path.exists() or config_path.stat().st_size == 0:
                raise RuntimeError("Downloaded config is empty")

            logger.info("Voice downloaded: %s", voice_id)
            return True

        except Exception as e:
            logger.error("Failed to download voice %s: %s", voice_id, e)
            for p in (self._get_voice_path(voice_id), self._get_config_path(voice_id)):
                try:
                    # Only remove files we created in this failed attempt is
                    # complex; verify_voice_file() guards reuse, so remove only
                    # empty/invalid files.
                    if p.exists() and not verify_voice_file(
                        p, AVAILABLE_VOICES[voice_id].get("sha256")
                    ):
                        p.unlink()
                except OSError:
                    pass
            return False

    def _load_model(self, voice_id: str):
        """Load Piper model for the specified voice."""
        try:
            import piper

            model_path = self._get_voice_path(voice_id)
            config_path = self._get_config_path(voice_id)

            if not self.is_voice_downloaded(voice_id):
                if not self.download_voice(voice_id):
                    raise RuntimeError(f"Failed to download voice: {voice_id}")

            # Load model
            self._model = piper.PiperVoice.load(str(model_path), str(config_path))
            self._current_voice = voice_id

        except Exception as e:
            raise RuntimeError(f"Failed to load Piper model: {e}") from e

    def synthesize(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ) -> tuple[np.ndarray, int]:
        """Synthesize text to audio."""
        from utils.security import validate_synthesis_text

        if not self._initialized:
            raise RuntimeError("Engine not initialized")
        text = validate_synthesis_text(text)
        logger.debug("Piper synthesize: %s", preview_text(text))

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

        if not audio_chunks:
            raise RuntimeError("Piper synthesis produced no audio")

        # Concatenate chunks
        audio = np.concatenate(audio_chunks)

        # Adjust speed by resampling
        if speed != 1.0:
            import scipy.signal

            new_length = int(len(audio) / speed)
            audio = scipy.signal.resample(audio, new_length).astype(np.float32)

        return audio, sample_rate

    def synthesize_streaming(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ) -> Generator[tuple[np.ndarray, int], None, None]:
        """Synthesize text to audio with streaming."""
        from utils.security import validate_synthesis_text

        if not self._initialized:
            raise RuntimeError("Engine not initialized")
        text = validate_synthesis_text(text)

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
            import piper  # noqa: F401

            return True
        except ImportError:
            return False
