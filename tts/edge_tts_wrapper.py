"""Edge TTS engine wrapper - Microsoft Edge online TTS service."""
import asyncio
import io
import os
import wave
import struct
import tempfile
import subprocess
import sys
import numpy as np
import json
import threading
from typing import List, Generator, Tuple
from .engine import TTSEngine, VoiceInfo

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

def _synthesize_to_file(text, voice_id, rate, output_path):
    """Synthesize text to mp3 file using edge_tts (runs in subprocess)."""
    import edge_tts
    import asyncio
    
    async def _do():
        communicate = edge_tts.Communicate(text, voice_id, rate=rate)
        await communicate.save(output_path)
    
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()

class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge TTS engine wrapper."""
    
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._voices = []
        self._current_process = None
        self._stop_event = threading.Event()
    
    def initialize(self) -> bool:
        """Initialize Edge TTS engine."""
        try:
            import edge_tts
            self._initialized = True
            return True
        except ImportError:
            print("edge-tts not installed. Run: pip install edge-tts")
            return False
    
    def get_voices(self) -> List[VoiceInfo]:
        """Get list of available voices."""
        if not self._initialized:
            return []
        
        return [
            VoiceInfo(id="ru-RU-DmitryNeural", name="Dmitry (Russian, male)", language="ru", gender="male"),
            VoiceInfo(id="ru-RU-SvetlanaNeural", name="Svetlana (Russian, female)", language="ru", gender="female"),
            VoiceInfo(id="en-US-BrianNeural", name="Brian (English, male)", language="en", gender="male"),
            VoiceInfo(id="en-US-EmmaNeural", name="Emma (English, female)", language="en", gender="female"),
        ]
    
    def _mp3_to_numpy(self, mp3_path: str) -> Tuple[np.ndarray, int]:
        """Convert MP3 to numpy array using ffmpeg."""
        try:
            try:
                import imageio_ffmpeg
                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                ffmpeg_path = "ffmpeg"
            
            wav_path = mp3_path.replace('.mp3', '.wav')
            subprocess.run(
                [ffmpeg_path, '-y', '-i', mp3_path, '-ar', '22050', '-ac', '1', wav_path],
                **_get_subprocess_kwargs(),
                check=True
            )
            
            with wave.open(wav_path, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                sample_rate = wf.getframerate()
            
            os.unlink(wav_path)
            return audio, sample_rate
            
        except Exception as e:
            raise RuntimeError(f"Failed to convert mp3: {e}")
    
    def _synthesize_via_subprocess(self, text, voice_id, rate, max_retries=3):
        """Synthesize via separate Python process to avoid asyncio thread issues."""
        # Write text to temp file to avoid repr() issues with long/special text
        text_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8')
        text_file.write(text)
        text_file.close()
        
        script_content = (
            "# -*- coding: utf-8 -*-\n"
            "import sys, os, tempfile, json, asyncio, time\n"
            "if sys.platform == 'win32':\n"
            "    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\n"
            "import edge_tts\n"
            "\n"
            "text_file = " + repr(text_file.name) + "\n"
            "with open(text_file, 'r', encoding='utf-8') as f:\n"
            "    text = f.read()\n"
            "voice_id = " + repr(voice_id) + "\n"
            "rate = " + repr(rate) + "\n"
            "\n"
            "if not text or not text.strip():\n"
            "    print(json.dumps({'error': 'Empty text'}))\n"
            "    sys.exit(1)\n"
            "\n"
            "if not voice_id:\n"
            "    print(json.dumps({'error': 'No voice selected'}))\n"
            "    sys.exit(1)\n"
            "\n"
            "max_retries = " + str(max_retries) + "\n"
            "for attempt in range(max_retries):\n"
            "    tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)\n"
            "    tmp_path = tmp.name\n"
            "    tmp.close()\n"
            "    \n"
            "    try:\n"
            "        async def _do():\n"
            "            communicate = edge_tts.Communicate(text, voice_id, rate=rate)\n"
            "            await communicate.save(tmp_path)\n"
            "        \n"
            "        loop = asyncio.new_event_loop()\n"
            "        try:\n"
            "            loop.run_until_complete(_do())\n"
            "        finally:\n"
            "            loop.close()\n"
            "        \n"
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
            "            os.unlink(tmp_path)\n"
            "        if attempt < max_retries - 1:\n"
            "            time.sleep(1)\n"
            "            continue\n"
            "        else:\n"
            "            print(json.dumps({'error': str(e)}))\n"
            "            sys.exit(1)\n"
        )
        
        tmp_script = tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8')
        tmp_script.write(script_content)
        tmp_script.close()
        
        try:
            self._current_process = subprocess.Popen(
                [sys.executable, tmp_script.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
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
                    info = json.loads(stdout.strip())
                    if 'error' in info:
                        raise RuntimeError(f"Edge TTS error: {info['error']}")
                    if 'path' in info:
                        return info['path']
                except json.JSONDecodeError:
                    pass
            
            if proc.returncode != 0:
                if self._stop_event and self._stop_event.is_set():
                    return None  # User pressed stop — process was killed
                raise RuntimeError(f"Edge TTS subprocess failed (code {proc.returncode}): {stderr}")
            
            raise RuntimeError("Edge TTS: No valid response from subprocess")
        finally:
            try:
                os.unlink(tmp_script.name)
            except:
                pass
            try:
                os.unlink(text_file.name)
            except:
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
    
    def synthesize(self, text: str, voice_id: str, speed: float = 1.0,
                   pitch: float = 1.0) -> Tuple[np.ndarray, int]:
        """Synthesize text to audio. Splits long texts automatically."""
        if not self._initialized:
            raise RuntimeError("Engine not initialized")
        
        if not text or not text.strip():
            raise RuntimeError("Text is empty")
        
        if not voice_id:
            raise RuntimeError("No voice selected")
        
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
                    except:
                        pass
            else:
                chunks = self._split_text(text, 500)
                all_audio = []
                sample_rate = None
                for ci, chunk in enumerate(chunks):
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
                        except:
                            pass
                
                if not all_audio:
                    if self._stop_event and self._stop_event.is_set():
                        return None  # User pressed stop
                    raise RuntimeError("No audio generated")
                
                return np.concatenate(all_audio), sample_rate
                    
        except Exception as e:
            if self._stop_event and self._stop_event.is_set():
                return None  # User pressed stop — suppress error
            raise RuntimeError(f"Edge TTS synthesis failed: {e}")
    
    def _split_text(self, text: str, max_len: int) -> List[str]:
        """Split text into chunks by sentence boundaries."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        for s in sentences:
            if len(current) + len(s) + 1 <= max_len:
                current = (current + " " + s).strip()
            else:
                if current:
                    chunks.append(current)
                current = s
        if current:
            chunks.append(current)
        return chunks if chunks else [text]
    
    def synthesize_streaming(self, text: str, voice_id: str, speed: float = 1.0,
                             pitch: float = 1.0) -> Generator[Tuple[np.ndarray, int], None, None]:
        """Synthesize text to audio with streaming (via subprocess)."""
        result = self.synthesize(text, voice_id, speed, pitch)
        if result is None:
            return  # User pressed stop
        audio, sample_rate = result
        
        chunk_size = 4096
        for i in range(0, len(audio), chunk_size):
            yield audio[i:i+chunk_size], sample_rate
    
    def is_available(self) -> bool:
        """Check if Edge TTS is available."""
        try:
            import edge_tts
            return True
        except ImportError:
            return False
    
    def download_voice(self, voice_id: str) -> bool:
        """No download needed for Edge TTS (online service)."""
        return True
