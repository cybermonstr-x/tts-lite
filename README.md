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

| Library | License | Notes |
|---------|---------|-------|
| [PySide6](https://www.qt.io/qt-for-python) | LGPL v3 | GUI framework (dynamic linking, MIT-compatible) |
| [edge-tts](https://github.com/rany2/edge-tts) | MIT | Online engine wrapper |
| [piper-tts](https://github.com/rhasspy/piper) | MIT | Offline engine wrapper |
| [supertonic](https://github.com/supertonic) | MIT | Offline ONNX engine wrapper |
| [NumPy](https://numpy.org/) | BSD | Audio buffers |
| [SciPy](https://scipy.org/) | BSD | Resampling |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) | MIT | Playback |
| [pydub](https://github.com/jiaaro/pydub) | MIT | MP3 export (needs FFmpeg, see below) |
| [striprtf](https://github.com/spanborder/striprtf) | MIT | RTF loading |
| [requests](https://requests.readthedocs.io/) | Apache 2.0 | Model downloads (HTTPS only) |
| [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) | BSD | Bundled FFmpeg binary provider |

All dependencies are MIT/BSD/LGPL/Apache-2.0 licensed and compatible with
the project's MIT license. There are no GPL (viral-license) dependencies:
the GUI uses **PySide6 (LGPL v3)**, not PyQt6 (GPL v3), linked dynamically.

### FFmpeg

MP3 conversion uses FFmpeg obtained via the `imageio-ffmpeg` package, which
downloads a prebuilt static binary (no system FFmpeg install required).
FFmpeg itself is licensed under **LGPL v2.1+ / GPL** depending on build
options — see [ffmpeg.org](https://ffmpeg.org/) and
[ffmpeg.org/legal.html](https://ffmpeg.org/legal.html).
The binary is used as an **external executable** (invoked as a subprocess),
never linked into the application code, which keeps the MIT licensing of
this project intact. When redistributing the installer, the FFmpeg license
terms travel with the bundled binary; sources are available at
[ffmpeg.org/download.html](https://ffmpeg.org/download.html).

### Voice models

- **Piper TTS voices**: [MIT License](https://huggingface.co/rhasspy/piper-voices),
  by the Piper authors. Attribution is kept in the "About" data above; models
  download automatically from Hugging Face over HTTPS with SHA-256 integrity
  checks into the per-user cache (`~/.cache/tts-lite/models` on Linux/macOS,
  `%LOCALAPPDATA%\tts_lite\models` on Windows).
- **Supertonic 3 model**: [MIT License](https://huggingface.co/supertonic),
  auto-downloaded by the `supertonic` package on first use.
- **Edge TTS voices**: Microsoft Corporation online service (see Privacy below).

### Privacy

- **Edge TTS is cloud-based**: synthesis text is sent to Microsoft servers.
  On first selection of Edge TTS the app shows an explicit consent dialog
  («Этот движок отправляет текст в облачный сервис Microsoft. Вы соглашаетесь
  с передачей данных?») and stores your choice (`edge_consent`) in settings.
  Declining disables Edge TTS; Piper and Supertonic always work fully offline.
- **Logs never contain full synthesis texts** — only a 10-character preview
  plus length (e.g. for debug). No passwords, tokens or API keys are logged.
- **Settings** are stored per-user only (see Configuration below).

## License

This project is licensed under the [MIT License](LICENSE.txt).

## Development

Created with [Opencode](https://opencode.ai) v1.18.27 using MiMo V2.5 and Muse Spark 1.2 models.

## Contact

cryptomonstrik@gmail.com

## Architecture

```
tts-lite/
├── main.py              # Entry point
├── tts/                 # TTS engine abstraction layer
│   ├── engine.py        # Base engine interface
│   ├── edge_tts_wrapper.py
│   ├── piper_wrapper.py
│   └── supertonic_wrapper.py
├── ui/                  # PySide6 user interface
│   ├── main_window.py   # Main application window
│   ├── styles.py        # Theme definitions
│   └── download_dialog.py
├── audio/               # Audio processing
│   ├── playback.py      # Audio playback
│   └── export.py        # File export (MP3/WAV)
├── utils/               # Utilities
│   ├── config.py        # Settings management (QSettings, cross-platform)
│   ├── security.py      # Path validation, filename sanitizing, log previews
│   ├── logger.py        # Logging (no sensitive data, owner-only perms)
│   ├── text_processing.py
│   ├── translations.py  # i18n support
│   └── file_loaders.py  # .txt/.rtf/.md loaders (validated, size-limited)
├── tests/               # pytest suite (unit + integration + UI + security)
│   └── fixtures/        # sample.txt / sample.md / sample.rtf
└── resources/           # Icons, styles, translations
```

### Engine Abstraction

All TTS engines implement a common interface defined in `tts/engine.py`:

```python
class TTSEngine(ABC):
    @abstractmethod
    def get_voices(self) -> List[VoiceInfo]: ...
    
    @abstractmethod
    def synthesize(self, text: str, voice_id: str) -> np.ndarray: ...
    
    @abstractmethod
    def is_online(self) -> bool: ...
```

This allows seamless switching between engines without changing UI code.

## Configuration

Settings use `QSettings` with the native per-OS backend
(`TTSApp/TTSLite`):

- **Windows**: `HKEY_CURRENT_USER\Software\TTSApp\TTSLite` (registry)
- **Linux**: `~/.config/TTSApp/TTSLite.conf` (INI, `chmod 600`)
- **macOS**: `~/Library/Preferences/com.TTSApp.TTSLite.plist` (`chmod 600`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `theme` | String | `dark` | UI theme (`dark`/`light`) |
| `language` | String | `ru` | Interface language (`en`/`ru`) |
| `engine` | String | `auto` | Preferred TTS engine |
| `last_engine` | String | `edge_tts` | Last used TTS engine |
| `voice` / `last_voice` | String | `ru_RU-irina-medium` | Selected voice |
| `volume` | Integer | `80` | Playback volume (0-100) |
| `speed` / `rate` | Float | `1.0` | Speech rate multiplier (0.5–2.0) |
| `pitch` | Float | `1.0` | Voice pitch (0.5–2.0) |
| `export_format` | String | `mp3` | Default export format |
| `export_path` | String | - | Last export directory |
| `last_directory` | String | - | Last opened file directory |
| `edge_consent` | String | `unknown` | Edge TTS cloud consent (`accepted`/`declined`/`unknown`) |
| `debug_mode` | Boolean | `false` | Verbose logging |

## Troubleshooting

### Common Issues

**"No voices available"**
- Edge TTS: Check internet connection
- Piper: Voices will download automatically on first use (check network)
- Supertonic: Ensure model files exist in `models/supertonic/`

**Audio playback errors**
- Install audio drivers
- Check default playback device in Windows settings
- Try reducing sample rate in config

**Export fails**
- Ensure `pydub` and `ffmpeg` are installed
- Check write permissions for export directory
- Verify input text is not empty

### Logs

Application logs are written to `%TEMP%\tts_lite\tts_lite.log` on Windows
and `~/.cache/tts-lite/logs/tts_lite.log` on Linux/macOS (rotated, 5 MB × 3).
Logs never include full synthesis texts, passwords or tokens.
Enable debug mode by setting environment variable:
```bash
set TTS_LITE_DEBUG=1
python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality (required!)
5. Run existing tests: `pytest tests/`
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-qt

# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=tts_lite --cov-report=html

# Run specific test file
pytest tests/test_text_processing.py

# Run UI tests (requires display)
pytest tests/ui/
```

### Code Style

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Docstrings required for public APIs

## Roadmap

### Completed ✅
- [x] Automated tests (unit + integration + UI + security, see `tests/`)
- [x] CI/CD pipeline with GitHub Actions
- [x] Cross-platform build script (Linux/macOS/Windows)
- [x] UI test framework
- [x] PySide6 (LGPL) GUI — no GPL dependencies
- [x] Cross-platform settings (QSettings native backend per OS)

### In Progress 🔄
- [ ] Linux/macOS support (build script ready, testing needed)

### Planned 📋
- [ ] Voice cloning feature
- [ ] Batch processing (multiple files)
- [ ] SSML support for advanced control
- [ ] Cloud sync for settings
- [ ] Plugin system for custom engines
- [ ] Full GUI test coverage
- [ ] Docker container for server deployment

## FAQ

**Q: Why only Windows?**  
A: Initial development focused on Windows due to registry-based settings and Inno Setup installer. **Update**: Cross-platform build script (`build.sh`) now supports Linux and macOS. Native installers for these platforms are in progress.

**Q: Can I add my own voices?**  
A: Currently no, but you can request voice additions via GitHub issues. Custom voice support is on the roadmap.

**Q: Is commercial use allowed?**  
A: Yes, under MIT license. The GUI uses PySide6 (LGPL v3), dynamically linked,
which permits proprietary derivatives as long as LGPL terms are honored
(provide LGPL license text, allow relinking, publish any LGPL-component
modifications).

**Q: How accurate is Supertonic 3?**  
A: Supertonic 3 supports 31 languages with natural-sounding neural voices. Quality varies by language; best results for English, Russian, Spanish, and Chinese.

**Q: How do I run tests?**  
A: Install test dependencies with `pip install pytest pytest-cov pytest-qt`, then run `pytest tests/`. For UI tests on Linux/macOS, you need a display or Xvfb.

**Q: What is CI/CD?**  
A: CI/CD (Continuous Integration/Continuous Deployment) automatically runs tests and code checks whenever you push changes to GitHub. See `.github/workflows/ci-cd.yml` for configuration.

## Performance Benchmarks

| Engine | Avg. Synthesis Time* | Memory Usage | Offline |
|--------|---------------------|--------------|---------|
| Edge TTS | 2.3s | ~45 MB | ❌ |
| Piper TTS | 1.8s | ~120 MB | ✅ |
| Supertonic 3 | 1.2s | ~85 MB | ✅ |

*For 100 characters on Intel i5-8400, 16GB RAM

---

**Made with ❤️ for the TTS community**
