@echo off
REM Скрипт для локальной сборки TTS Lite на Windows
REM Запускать из Git Bash или Command Prompt

echo =========================================
echo TTS Lite - Локальная сборка (Windows)
echo =========================================

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Установите Python 3.10 или выше.
    exit /b 1
)

echo [OK] Python найден: 
python --version

REM Создание виртуального окружения
if not exist "venv" (
    echo.
    echo Создание виртуального окружения...
    python -m venv venv
    echo [OK] Виртуальное окружение создано
) else (
    echo [OK] Виртуальное окружение уже существует
)

REM Активация виртуального окружения
echo.
echo Активация виртуального окружения...
call venv\Scripts\activate.bat
echo [OK] Виртуальное окружение активировано

REM Обновление pip
echo.
echo Обновление pip...
python -m pip install --upgrade pip
echo [OK] pip обновлён

REM Установка зависимостей
echo.
echo Установка зависимостей...
pip install -r requirements.txt
echo [OK] Зависимости установлены

REM Установка инструментов для сборки
echo.
echo Установка инструментов для сборки...
pip install pyinstaller pytest pytest-cov flake8 black isort mypy
echo [OK] Инструменты установлены

REM Запуск тестов
echo.
set /p run_tests="Запустить тесты? (y/n): "
if "%run_tests%"=="y" (
    echo Запуск тестов...
    pytest tests/ -v --tb=short
    if errorlevel 1 (
        echo [WARNING] Некоторые тесты не прошли
    ) else (
        echo [OK] Тесты завершены успешно
    )
) else (
    echo [INFO] Пропуск тестов
)

REM Сборка исполняемого файла
echo.
echo Сборка исполняемого файла с помощью PyInstaller...
pyinstaller build.spec --clean --noconfirm

REM Проверка результата
echo.
echo Проверка результата сборки...
if exist "dist\TTS_Lite\TTS_Lite.exe" (
    echo [OK] Сборка успешна!
    echo.
    echo Исполняемый файл находится:
    echo   dist\TTS_Lite\TTS_Lite.exe
) else (
    echo [ERROR] Сборка не удалась - исполняемый файл не найден
    exit /b 1
)

echo.
echo =========================================
echo Сборка завершена успешно!
echo =========================================
echo.
echo Для запуска приложения:
echo   .\dist\TTS_Lite\TTS_Lite.exe
echo.

pause
