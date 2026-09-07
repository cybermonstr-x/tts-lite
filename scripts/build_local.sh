#!/bin/bash
# Скрипт для локальной сборки TTS Lite
# Работает на Linux, macOS и Windows (Git Bash)

set -e

echo "========================================="
echo "TTS Lite - Локальная сборка"
echo "========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Без цвета

# Функция для печати статусов
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Определение ОС
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    print_status "Обнаружена ОС: Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    print_status "Обнаружена ОС: macOS"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
    print_status "Обнаружена ОС: Windows"
else
    OS="unknown"
    print_warning "Неизвестная ОС: $OSTYPE. Продолжаем в универсальном режиме..."
fi

# Проверка наличия Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "Python не найден! Установите Python 3.10 или выше."
    exit 1
fi

# Используем python3 или python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

print_status "Используется: $($PYTHON_CMD --version)"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo ""
    echo "Создание виртуального окружения..."
    $PYTHON_CMD -m venv venv
    print_status "Виртуальное окружение создано"
else
    print_status "Виртуальное окружение уже существует"
fi

# Активация виртуального окружения
echo ""
echo "Активация виртуального окружения..."
if [ "$OS" == "windows" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
print_status "Виртуальное окружение активировано"

# Обновление pip
echo ""
echo "Обновление pip..."
pip install --upgrade pip
print_status "pip обновлён"

# Установка зависимостей
echo ""
echo "Установка зависимостей..."
pip install -r requirements.txt
print_status "Зависимости установлены"

# Установка инструментов для сборки
echo ""
echo "Установка инструментов для сборки..."
pip install pyinstaller pytest pytest-cov flake8 black isort mypy
print_status "Инструменты установлены"

# Запуск тестов (опционально)
echo ""
read -p "Запустить тесты? (y/n): " run_tests
if [ "$run_tests" = "y" ] || [ "$run_tests" = "Y" ]; then
    echo "Запуск тестов..."
    pytest tests/ -v --tb=short || print_warning "Некоторые тесты не прошли"
    print_status "Тесты завершены"
else
    print_warning "Пропуск тестов"
fi

# Сборка исполняемого файла
echo ""
echo "Сборка исполняемого файла с помощью PyInstaller..."
pyinstaller build.spec --clean --noconfirm

# Проверка результата
echo ""
echo "Проверка результата сборки..."
if [ "$OS" == "windows" ]; then
    if [ -f "dist/TTS_Lite/TTS_Lite.exe" ] || [ -f "dist/TTS_Lite.exe" ]; then
        print_status "Сборка успешна!"
        echo ""
        echo "Исполняемый файл находится:"
        echo "  dist/TTS_Lite/TTS_Lite.exe"
    else
        print_error "Сборка не удалась - исполняемый файл не найден"
        exit 1
    fi
elif [ "$OS" == "macos" ]; then
    if [ -d "dist/TTS_Lite.app" ] || [ -f "dist/TTS_Lite" ]; then
        print_status "Сборка успешна!"
        echo ""
        echo "Приложение находится:"
        echo "  dist/TTS_Lite.app"
    else
        print_error "Сборка не удалась - приложение не найдено"
        exit 1
    fi
else
    if [ -d "dist/TTS_Lite" ] || [ -f "dist/TTS_Lite" ]; then
        print_status "Сборка успешна!"
        echo ""
        echo "Исполняемый файл находится:"
        echo "  dist/TTS_Lite/TTS_Lite"
    else
        print_error "Сборка не удалась - исполняемый файл не найден"
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "Сборка завершена успешно!"
echo "========================================="
echo ""
echo "Для запуска приложения:"
if [ "$OS" == "windows" ]; then
    echo "  ./dist/TTS_Lite/TTS_Lite.exe"
elif [ "$OS" == "macos" ]; then
    echo "  open ./dist/TTS_Lite.app"
else
    echo "  ./dist/TTS_Lite/TTS_Lite"
fi
echo ""
