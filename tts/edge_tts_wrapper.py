"""Edge TTS engine wrapper - Microsoft Edge online TTS service.

Privacy notice: this engine sends the synthesis text to the Microsoft
cloud service. The UI must obtain explicit user consent before first use
(see ``utils.config.Config.edge_consent`` and ``EDGE_CONSENT_MESSAGE``).

Security: user text/voice are never embedded into generated code and never
passed through a shell. Synthesis parameters travel to the worker
subprocess via a JSON job file; the worker script itself is static.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import wave
from collections.abc import Generator

import numpy as np

from utils.logger import get_logger, preview_text

from .engine import TTSEngine, VoiceInfo

logger = get_logger(__name__)

EDGE_CONSENT_MESSAGE = (
    "Движок Edge TTS отправляет текст в облачный сервис Microsoft "
    "для синтеза речи. Вы соглашаетесь с передачей данных?"
)
EDGE_CONSENT_MESSAGE_EN = (
    "The Edge TTS engine sends text to the Microsoft cloud service "
    "for speech synthesis. Do you agree to transmit the data?"
)

ALLOWED_VOICES = {
    "ru-RU-DmitryNeural",
    "ru-RU-SvetlanaNeural",
    "en-US-BrianNeural",
    "en-US-EmmaNeural",
}

# Static worker script: reads job JSON from sys.argv[1], no user data in code.
_WORKER_SCRIPT = (
    "# -*- coding: utf-8 -*-\n"
    "import sys, os, tempfile, json, asyncio, time\n"
    "if sys.platform == 'win32':\n"
    "    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\n"
    "import edge_tts\n"
    "job_path = sys.argv[1]\n"
    "with open(job_path, 'r', encoding='utf-8') as f:\n"
    "    job = json.load(f)\n"
    "text = job.get('text', '')\n"
    "voice_id = job.get('voice_id', '')\n"
    "rate = job.get('rate', '+0%')\n"
    "max_retries = int(job.get('max_retries', 3))\n"
    "if not text or not text.strip():\n"
    "    print(json.dumps({'error': 'Empty text'}))\n"
    "    sys.exit(1)\n"
    "if not voice_id:\n"
    "    print(json.dumps({'error': 'No voice selected'}))\n"
    "    sys.exit(1)\n"
    "for attempt in range(max_retries):\n"
    "    tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)\n"
    "    tmp_path = tmp.name\n"
    "    tmp.close()\n"
    "    try:\n"
    "        async def _do():\n"
    "            communicate = edge_tts.Communicate(text, voice_id, rate=rate)\n"
    "            await communicate.save(tmp_path)\n"
    "        loop = asyncio.new_event_loop()\n"
    "        try:\n"
    "            loop.run_until_complete(_do())\n"
    "        finally:\n"
    "            loop.close()\n"
    "        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:\n"
    "            print(json.dumps({'path': tmp_path, 'size': os.path.getsize(tmp_path)}))\n"
    "            sys.exit(0)\n"
    "        else:\n"
    "            if os.path.exists(tmp_path):\n"
    "                os.unlink(tmp_path)\n"
    "            if attempt < max_retries - 1:\n"
    "                time.sleep(1)\n"
    "                continue\n"
    "            else:\n"
    "                print(json.dumps({'error': 'No audio generated after retries'}))\n"
    "                sys.exit(1)\n"
    "    except Exception as e:\n"
    "        if os.path.exists(tmp_path):\n"
    "            try:\n"
    "                os.unlink(tmp_path)\n"
    "            except OSError:\n"
    "                pass\n"
    "        if attempt < max_retries - 1:\n"
    "            time.sleep(1)\n"
    "            continue\n"
    "        else:\n"
    "            print(json.dumps({'error': str(e)}))\n"
    "            sys.exit(1)\n"
)


def _get_subprocess_kwargs():
    """Get subprocess kwargs to hide console window on Windows."""
    kwargs = {"capture_output": True}
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def check_edge_consent(config, parent=None) -> bool:
    """Ask the user for Edge TTS cloud consent if not decided yet.

    Returns True if the user consented (or had consented before).
    Persists the choice in ``config``. Safe to call without a GUI
    (returns the stored value, default False when unknown).
    """
    try:
        state = config.edge_consent
    except AttributeError:
        state = "unknown"
    if state == "accepted":
        return True
    if state == "declined":
        return False
    if parent is None:
        return False
    try:
        from PySide6.QtWidgets import QMessageBox

        lang = getattr(config, "language", "ru")
        msg = EDGE_CONSENT_MESSAGE if lang == "ru" else EDGE_CONSENT_MESSAGE_EN
        title = (
            "Edge TTS — передача данных" if lang == "ru" else "Edge TTS — data transfer"
        )
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(title)
        box.setText(msg)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        accepted = box.exec() == QMessageBox.StandardButton.Yes
    except Exception:
        accepted = False
    try:
        config.set_edge_consent(accepted)
    except Exception:
        pass
    return accepted


class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge TTS engine wrapper."""

    def __init__(self):
        super().__init__()
        self._initialized = False
        self._current_process = None
        self._stop_event = threading.Event()

    def initialize(self) -> bool:
        """Initialize Edge TTS engine."""
        try:
            import edge_tts  # noqa: F401

            self._initialized = True
            return True
        except ImportError:
            logger.error("edge-tts not installed. Run: pip install edge-tts")
            return False

    def get_voices(self) -> list[VoiceInfo]:
        """Get list of available voices."""
        if not self._initialized:
            return []

        return [
            VoiceInfo(
                id="ru-RU-DmitryNeural",
                name="Dmitry (Russian, male)",
                language="ru",
                gender="male",
            ),
            VoiceInfo(
                id="ru-RU-SvetlanaNeural",
                name="Svetlana (Russian, female)",
                language="ru",
                gender="female",
            ),
            VoiceInfo(
                id="en-US-BrianNeural",
                name="Brian (English, male)",
                language="en",
                gender="male",
            ),
            VoiceInfo(
                id="en-US-EmmaNeural",
                name="Emma (English, female)",
                language="en",
                gender="female",
            ),
        ]

    def _validate_request(self, text: str, voice_id: str) -> str:
        """Validate synthesis request; returns stripped text."""
        from utils.security import validate_synthesis_text

        text = validate_synthesis_text(text)
        if not voice_id:
            raise RuntimeError("No voice selected")
        if voice_id not in ALLOWED_VOICES:
            raise RuntimeError(f"Unknown Edge voice: {voice_id}")
        return text

    def _mp3_to_numpy(self, mp3_path: str) -> tuple[np.ndarray, int]:
        """Convert MP3 to numpy array using ffmpeg."""
        wav_path = mp3_path + ".wav" if mp3_path.endswith(".mp3") else mp3_path + ".wav"
        try:
            try:
                import imageio_ffmpeg

                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                ffmpeg_path = "ffmpeg"

            subprocess.run(
                [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    mp3_path,
                    "-ar",
                    "22050",
                    "-ac",
                    "1",
                    wav_path,
                ],
                **_get_subprocess_kwargs(),
                check=True,
            )

            with wave.open(wav_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                audio = (
                    np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                )
                sample_rate = wf.getframerate()

            return audio, sample_rate

        except Exception as e:
            raise RuntimeError(f"Failed to convert mp3: {e}") from e
        finally:
            try:
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
            except OSError:
                pass

    def _synthesize_direct(self, text, voice_id, rate, max_retries=3):
        """Direct synthesis without subprocess — used in frozen exe.

        The subprocess path spawns sys.executable. In a PyInstaller
        --windowed build that is TTS_Lite.exe itself, spawning it opens
        a second GUI window. For frozen builds we run edge-tts in-process.
        """
        import asyncio

        import edge_tts

        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                pass

        last_error = None
        for attempt in range(max_retries):
            if self._stop_event and self._stop_event.is_set():
                return None
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:

                async def _do():
                    communicate = edge_tts.Communicate(text, voice_id, rate=rate)
                    await communicate.save(tmp_path)

                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_do())
                finally:
                    loop.close()

                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    return tmp_path
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                if attempt < max_retries - 1:
                    import time

                    time.sleep(1)
                    continue
                raise RuntimeError("No audio generated after retries")
            except Exception as e:
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                if self._stop_event and self._stop_event.is_set():
                    return None
                last_error = e
                if attempt < max_retries - 1:
                    import time

                    time.sleep(1)
                    continue
                raise RuntimeError(f"Edge TTS error: {e}") from e
        if last_error:
            raise RuntimeError(f"Edge TTS error: {last_error}") from last_error
        raise RuntimeError("Edge TTS: No valid response")

    def _synthesize_via_subprocess(self, text, voice_id, rate, max_retries=3):
        """Synthesize via separate Python process to avoid asyncio thread issues.

        No shell is used (argv list) and no user data is embedded in code:
        parameters are passed as a JSON job file.
        In frozen (PyInstaller) builds sys.executable is the exe itself,
        spawning it would open a second GUI window — use direct mode there.
        """
        if getattr(sys, "frozen", False):
            return self._synthesize_direct(text, voice_id, rate, max_retries)

        job_file = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        )
        try:
            json.dump(
                {
                    "text": text,
                    "voice_id": voice_id,
                    "rate": rate,
                    "max_retries": max_retries,
                },
                job_file,
            )
            job_file.close()
            job_path = job_file.name
        except Exception:
            job_file.close()
            raise

        tmp_script = tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        )
        tmp_script.write(_WORKER_SCRIPT)
        tmp_script.close()

        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            self._current_process = subprocess.Popen(
                [sys.executable, tmp_script.name, job_path],
                **popen_kwargs,
            )
            proc = self._current_process

            try:
                stdout, stderr = proc.communicate(timeout=300)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                if self._stop_event and self._stop_event.is_set():
                    return None  # User pressed stop — no error
                raise RuntimeError("Edge TTS subprocess timed out (300s)")
            finally:
                self._current_process = None

            # If user pressed stop, subprocess was killed — no error
            if self._stop_event and self._stop_event.is_set():
                return None

            if stdout:
                try:
                    info = json.loads(stdout.strip().splitlines()[-1])
                    if "error" in info:
                        raise RuntimeError(f"Edge TTS error: {info['error']}")
                    if "path" in info:
                        return info["path"]
                except (json.JSONDecodeError, IndexError):
                    pass

            if proc.returncode != 0:
                if self._stop_event and self._stop_event.is_set():
                    return None  # User pressed stop — process was killed
                raise RuntimeError(
                    f"Edge TTS subprocess failed (code {proc.returncode}): {stderr}"
                )

            raise RuntimeError("Edge TTS: No valid response from subprocess")
        finally:
            for p in (tmp_script.name, job_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def stop(self):
        """Stop current synthesis."""
        self._stop_event.set()
        proc = self._current_process
        self._current_process = None
        if proc:
            try:
                proc.kill()
                proc.wait(timeout=2.0)
            except Exception:
                pass

    def synthesize(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ):
        """Synthesize text to audio. Splits long texts automatically."""
        if not self._initialized:
            raise RuntimeError("Engine not initialized")

        text = self._validate_request(text, voice_id)
        logger.debug("Edge synthesize: %s voice=%s", preview_text(text), voice_id)

        self._stop_event.clear()

        try:
            rate_percent = int((speed - 1.0) * 100)
            rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

            if len(text) <= 500:
                if self._stop_event.is_set():
                    return None

                tmp_path = self._synthesize_via_subprocess(text, voice_id, rate)
                if tmp_path is None:
                    return None  # User pressed stop
                try:
                    audio, sample_rate = self._mp3_to_numpy(tmp_path)
                    return audio, sample_rate
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            else:
                chunks = self._split_text(text, 500)
                all_audio = []
                sample_rate = None
                for chunk in chunks:
                    if self._stop_event.is_set():
                        return None

                    if not chunk.strip():
                        continue
                    tmp_path = self._synthesize_via_subprocess(chunk, voice_id, rate)
                    if tmp_path is None:
                        return None  # User pressed stop
                    try:
                        audio, sr = self._mp3_to_numpy(tmp_path)
                        all_audio.append(audio)
                        sample_rate = sr
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                if not all_audio:
                    if self._stop_event and self._stop_event.is_set():
                        return None  # User pressed stop
                    raise RuntimeError("No audio generated")

                return np.concatenate(all_audio), sample_rate

        except Exception as e:
            if self._stop_event and self._stop_event.is_set():
                return None  # User pressed stop — suppress error
            raise RuntimeError(f"Edge TTS synthesis failed: {e}") from e

    def _split_text(self, text: str, max_len: int) -> list[str]:
        """Split text into chunks by sentence boundaries."""
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current = ""
        for s in sentences:
            if len(current) + len(s) + 1 <= max_len:
                current = (current + " " + s).strip()
            else:
                if current:
                    chunks.append(current)
                if len(s) > max_len:
                    # Hard-split overlong sentence to guarantee progress.
                    for i in range(0, len(s), max_len):
                        chunks.append(s[i : i + max_len])
                    current = ""
                else:
                    current = s
        if current:
            chunks.append(current)
        return chunks if chunks else [text]

    def synthesize_streaming(
        self, text: str, voice_id: str, speed: float = 1.0, pitch: float = 1.0
    ) -> Generator[tuple[np.ndarray, int], None, None]:
        """Synthesize text to audio with streaming (via subprocess)."""
        result = self.synthesize(text, voice_id, speed, pitch)
        if result is None:
            return  # User pressed stop
        audio, sample_rate = result

        chunk_size = 4096
        for i in range(0, len(audio), chunk_size):
            yield audio[i : i + chunk_size], sample_rate

    def is_available(self) -> bool:
        """Check if Edge TTS is available."""
        try:
            import edge_tts  # noqa: F401

            return True
        except ImportError:
            return False

    def download_voice(self, voice_id: str) -> bool:
        """No download needed for Edge TTS (online service)."""
        if voice_id not in ALLOWED_VOICES:
            raise ValueError(f"Unknown Edge voice: {voice_id}")
        return True
