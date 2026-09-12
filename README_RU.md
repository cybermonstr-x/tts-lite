# TTS Lite

[![Лицензия: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-lightgrey.svg)](https://www.microsoft.com/)

Лёгкая десктопная программа для озвучки текста на Windows, Linux и macOS с тремя движками: Edge TTS (онлайн), Piper TTS (офлайн) и Supertonic 3 (офлайн, ONNX).

[English version](README.md) · [Сайт](https://cybermonstr-x.github.io/tts-lite/) · [Релизы](https://github.com/cybermonstr-x/tts-lite/releases)

## Возможности

- **3 движка TTS**: Edge TTS (онлайн, нейросетевые голоса), Piper TTS (офлайн), Supertonic 3 (офлайн, ONNX, 31 язык)
- **18 голосов**: 4 Edge TTS + 4 Piper + 10 Supertonic
- **Файлы**: `.txt`, `.rtf`, `.md`
- **Воспроизведение**: озвучка всего текста и предпросмотр 200 символов
- **Экспорт**: MP3/WAV с авто-именами
- **Интерфейс**: тёмная/светлая темы, русский/английский язык
- **Мгновенный стоп**: прерывание синтеза и воспроизведения

## Установка

### Из установщика

Скачайте `setup_TTS_Lite_1.0.5.exe` из [Releases](https://github.com/cybermonstr-x/tts-lite/releases) и запустите.

### Из исходников

```bash
git clone https://github.com/cybermonstr-x/tts-lite.git
cd tts-lite
pip install -r requirements.txt
python main.py
```

## Использование

1. Откройте файл `.txt`/`.rtf`/`.md` или вставьте текст
2. Выберите движок и голос
3. Нажмите **Воспроизвести** для всего текста
4. Выделите текст и нажмите **Прослушать (200)** для предпросмотра
5. Нажмите **Стоп** для прерывания
6. Экспорт: выберите `mp3`/`wav`, нажмите **Озвучить файл** → **Сохранить как**

## Голоса, зависимости, приватность, лицензии

См. [README.md](README.md) (разделы Voices, Dependencies, Privacy) — актуально для обеих языковых версий.

## Контакты

cryptomonstrik@gmail.com

## Лицензия

MIT — см. [LICENSE.txt](LICENSE.txt)
