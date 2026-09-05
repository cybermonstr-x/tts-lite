#!/bin/bash
# Cross-platform build script for TTS Lite
# Works on Linux, macOS, and Windows (Git Bash)

set -e

echo "========================================="
echo "TTS Lite - Cross-Platform Build Script"
echo "========================================="

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "Detected: Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "Detected: macOS"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
    echo "Detected: Windows"
else
    OS="unknown"
    echo "Warning: Unknown OS type: $OSTYPE"
    echo "Proceeding with generic build..."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
if [ "$OS" == "windows" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install build tools
echo ""
echo "Installing build tools..."
pip install pyinstaller pytest pytest-cov flake8

# Run tests
echo ""
echo "Running tests..."
pytest tests/ -v --tb=short

# Build executable with PyInstaller
echo ""
echo "Building executable with PyInstaller..."
pyinstaller build.spec --clean

# Check build output
echo ""
echo "Checking build output..."
if [ -d "dist/tts_lite" ] || [ -f "dist/tts_lite.exe" ]; then
    echo "✓ Build successful!"
    echo ""
    echo "Executable location:"
    if [ "$OS" == "windows" ]; then
        echo "  dist/tts_lite.exe"
    elif [ "$OS" == "macos" ]; then
        echo "  dist/tts_lite.app"
    else
        echo "  dist/tts_lite"
    fi
else
    echo "✗ Build failed - executable not found"
    exit 1
fi

echo ""
echo "========================================="
echo "Build completed successfully!"
echo "========================================="
