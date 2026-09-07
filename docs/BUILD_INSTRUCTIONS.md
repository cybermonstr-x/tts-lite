# Инструкция по сборке TTS Lite

## Содержание

1. [Локальная сборка](#локальная-сборка)
2. [Автоматическая сборка через GitHub Actions](#автоматическая-сборка-через-github-actions)
3. [Устранение проблем](#устранение-проблем)

---

## Локальная сборка

### Требования

- **Python 3.10 или выше** ([скачать](https://www.python.org/downloads/))
- **Git** (опционально, для клонирования репозитория)
- **Операционная система**: Windows 10/11, Linux, macOS

### Быстрый старт

#### Windows

1. Откройте PowerShell или Command Prompt в папке проекта
2. Запустите скрипт сборки:
   ```batch
   scripts\build_local.bat
   ```

Или выполните команды вручную:

```batch
# Создание виртуального окружения
python -m venv venv

# Активация виртуального окружения
venv\Scripts\activate

# Обновление pip
python -m pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt

# Установка PyInstaller
pip install pyinstaller

# Сборка приложения
pyinstaller build.spec --clean --noconfirm
```

#### Linux / macOS

1. Откройте терминал в папке проекта
2. Сделайте скрипт исполняемым и запустите:
   ```bash
   chmod +x scripts/build_local.sh
   ./scripts/build_local.sh
   ```

Или выполните команды вручную:

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt

# Установка PyInstaller
pip install pyinstaller

# Сборка приложения
pyinstaller build.spec --clean --noconfirm
```

### Результат сборки

После успешной сборки исполняемый файл будет находиться в папке:

- **Windows**: `dist/TTS_Lite/TTS_Lite.exe`
- **Linux**: `dist/TTS_Lite/TTS_Lite`
- **macOS**: `dist/TTS_Lite.app`

### Запуск приложения

```bash
# Windows
.\dist\TTS_Lite\TTS_Lite.exe

# Linux
./dist/TTS_Lite/TTS_Lite

# macOS
open ./dist/TTS_Lite.app
```

---

## Автоматическая сборка через GitHub Actions

### Что такое GitHub Actions?

GitHub Actions — это инструмент непрерывной интеграции и доставки (CI/CD), который автоматически выполняет тесты, линтинг и сборку вашего проекта при каждом изменении кода.

### Настройка автоматической сборки

#### Шаг 1: Проверка наличия workflow-файлов

В репозитории уже есть два workflow-файла:

1. **`.github/workflows/ci-cd.yml`** — базовый CI/CD пайплайн (тесты + линтинг)
2. **`.github/workflows/build-release.yml`** — расширенный пайплайн с сборкой для всех платформ и созданием релизов

#### Шаг 2: Активация GitHub Actions

1. Перейдите на страницу вашего репозитория на GitHub
2. Нажмите вкладку **Actions**
3. Если Actions отключены, нажмите **Enable GitHub Actions**

#### Шаг 3: Настройка триггеров

Workflow файлы настроены на запуск при следующих событиях:

- **Push в ветку `main`** — запускает тесты и линтинг
- **Pull Request в `main`** — запускает тесты и линтинг
- **Создание тега версии** (например, `v1.0.0`) — запускает сборку для всех платформ и создаёт релиз

#### Шаг 4: Создание релиза

Для автоматического создания релиза с бинарными файлами:

1. Убедитесь, что все тесты проходят успешно
2. Создайте тег версии:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. GitHub Actions автоматически:
   - Запустит тесты и линтинг
   - Соберёт приложение для Windows, Linux и macOS
   - Создаст архивы с исполняемыми файлами
   - Опубликует релиз на GitHub с вложениями

### Мониторинг сборок

1. Перейдите на вкладку **Actions** в вашем репозитории
2. Выберите нужный workflow из списка слева
3. Кликните на конкретный запуск для просмотра логов
4. Артефакты сборки доступны в разделе **Artifacts** каждого успешного запуска

### Настройка переменных окружения (опционально)

Если вам нужно настроить дополнительные параметры:

1. Перейдите в **Settings → Secrets and variables → Actions**
2. Добавьте необходимые переменные в разделе **Variables**
3. Секретные ключи (токены, пароли) добавьте в разделе **Secrets**

### Примеры использования

#### Только тестирование при пуше

```yaml
on:
  push:
    branches: [ main ]
```

#### Сборка только при создании тега

```yaml
on:
  push:
    tags:
      - 'v*'
```

#### Еженедельная сборка

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Каждое воскресенье в 00:00 UTC
```

---

## Устранение проблем

### Ошибки при локальной сборке

#### "Python not found"

**Решение**: Установите Python 3.10+ с официального сайта https://www.python.org/downloads/

При установке на Windows убедитесь, что отмечена опция **"Add Python to PATH"**.

#### "ModuleNotFoundError"

**Решение**: Убедитесь, что виртуальное окружение активировано и все зависимости установлены:

```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# Переустановка зависимостей
pip install -r requirements.txt --force-reinstall
```

#### "PyInstaller build failed"

**Решение**:

1. Очистите предыдущие сборки:
   ```bash
   python build.py --clean
   ```

2. Проверьте наличие файла спецификации `build.spec`

3. Попробуйте собрать с флагом отладки:
   ```bash
   pyinstaller build.spec --debug=all
   ```

#### Проблемы с зависимостями на macOS/Linux

**Решение**: Установите системные зависимости:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-dev build-essential libasound2-dev

# Fedora/CentOS
sudo dnf install -y python3-devel gcc alsa-lib-devel

# macOS (требуется Homebrew)
brew install portaudio
```

### Ошибки GitHub Actions

#### Workflow не запускается

**Причина**: GitHub Actions могут быть отключены для репозитория.

**Решение**:
1. Перейдите в **Settings → Actions → General**
2. Включите **Allow all actions and reusable workflows**

#### Тесты не проходят

**Причина**: Проблемы с кодом или зависимостями.

**Решение**:
1. Проверьте логи failed job
2. Запустите тесты локально: `pytest tests/ -v`
3. Исправьте ошибки и запушьте изменения снова

#### Сборка не создаёт артефакты

**Причина**: Неправильный путь к файлам или ошибка в spec-файле.

**Решение**:
1. Проверьте пути в файле `build.spec`
2. Убедитесь, что PyInstaller завершается успешно
3. Проверьте логи шага **Build executable**

#### Лимиты GitHub Actions

Бесплатный тариф GitHub включает:
- 2000 минут сборки в месяц для публичных репозиториев
- 500 МБ места для артефактов
- Хранение артефактов до 90 дней

**Решение**: Для увеличения лимитов рассмотрите переход на платный тариф или используйте self-hosted runners.

---

## Дополнительные ресурсы

- [Документация PyInstaller](https://pyinstaller.org/en/stable/)
- [Документация GitHub Actions](https://docs.github.com/en/actions)
- [Создание релизов на GitHub](https://docs.github.com/en/repositories/releasing-projects-on-github)

---

## Контакты

По вопросам сборки обращайтесь: cryptomonstrik@gmail.com
