# TTS Lite

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-lightgrey.svg)](https://www.microsoft.com/)

Lightweight text-to-speech desktop application for Windows with Edge TTS (online), Piper TTS (offline), and Supertonic 3 (offline, ONNX).

## Features

- **3 TTS engines**: Edge TTS (online, neural voices), Piper TTS (offline), Supertonic 3 (offline, ONNX, 31 languages)
- **18 voices**: 4 Edge TTS + 4 Piper + 10 Supertonic
- **File support**: `.txt`, `.rtf`, `.md`
- **Playback**: Full text synthesis and 200-character selection preview
- **Export**: MP3/WAV with auto-generated filenames
- **UI**: Dark/Light themes, Russian/English interface
- **Responsive stop**: Immediate interruption of synthesis and playback

## Screenshots

<!-- Add screenshots here -->

## Installation

### From installer

Download `setup_TTS_Lite_1.0.0.exe` and run it. No admin rights required.

### From source

```bash
git clone https://github.com/yourusername/tts-lite.git
cd tts-lite
pip install -r requirements.txt
python main.py
```

## Usage

1. Open a text file (`.txt`, `.rtf`, `.md`) or paste text directly
2. Select TTS engine and voice
3. Click **Play** to synthesize the entire text
4. Select text and click **Preview (200)** to hear the first 200 characters
5. Click **Stop** to interrupt playback
6. Export: choose format (`mp3`/`wav`), click **Synthesize** then **Save As**

## Voices

### Edge TTS (online, requires internet)

| Voice | Language | Gender |
|-------|----------|--------|
| ru-RU-DmitryNeural | Russian | Male |
| ru-RU-SvetlanaNeural | Russian | Female |
| en-US-BrianNeural | English | Male |
| en-US-EmmaNeural | English | Female |

### Piper TTS (offline)

| Voice | Language | Gender |
|-------|----------|--------|
| ru_RU-irina-medium | Russian | Female |
| ru_RU-ruslan-medium | Russian | Male |
| en_US-lessac-medium | English | Male |
| en_US-amy-medium | English | Female |

Voices are downloaded automatically on first use.

### Supertonic 3 (offline, ONNX, 31 languages)

| Voice | Description |
|-------|-------------|
| M1 | Male (clear) |
| M2 | Male (calm) |
| M3 | Male (energetic) |
| M4 | Male (deep) |
| M5 | Male (soft) |
| F1 | Female (clear) |
| F2 | Female (calm) |
| F3 | Female (energetic) |
| F4 | Female (deep) |
| F5 | Female (soft) |

## Building

```bash
# Build executable
python build.py

# Build installer (requires Inno Setup)
& "C:\Program Files\Inno Setup 7\ISCC.exe" installer.iss
```

## Dependencies

| Library | License |
|---------|---------|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | GPL v3 |
| [edge-tts](https://github.com/rany2/edge-tts) | MIT |
| [piper-tts](https://github.com/rhasspy/piper) | MIT |
| [supertonic](https://github.com/supertonic) | MIT |
| [NumPy](https://numpy.org/) | BSD |
| [SciPy](https://scipy.org/) | BSD |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) | MIT |
| [pydub](https://github.com/jiaaro/pydub) | MIT |
| [striprtf](https://github.com/spanborder/striprtf) | MIT |
| [requests](https://requests.readthedocs.io/) | Apache 2.0 |
| [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) | BSD |

### Voice models

- **Piper TTS voices**: [MIT License](https://huggingface.co/rhasspy/piper-voices)
- **Supertonic 3 model**: [MIT License](https://huggingface.co/supertonic)
- **Edge TTS voices**: Microsoft Corporation (online service)

## License

This project is licensed under the [MIT License](LICENSE.txt).

## Development

Created with [Opencode](https://opencode.ai) v1.18.27 using MiMo V2.5 and Muse Spark 1.2 models.

## Contact

cryptomonstrik@gmail.com
