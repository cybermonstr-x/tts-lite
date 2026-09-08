"""
Build script for Text-to-Speech application.

Usage:
    python build.py              # Build application
    python build.py --clean      # Clean build directories
    python build.py --installer  # Build installer (requires Inno Setup)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Directories
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
SPEC_FILE = Path("build.spec")


def clean():
    """Clean build directories."""
    print("Cleaning build directories...")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    print("Clean complete.")


def build():
    """Build the application using PyInstaller."""
    print("Building application...")

    # Check if PyInstaller is installed
    try:
        import PyInstaller

        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("Error: PyInstaller not installed.")
        print("Install with: pip install pyinstaller")
        sys.exit(1)

    # Check if spec file exists
    if not SPEC_FILE.exists():
        print(f"Error: Spec file not found: {SPEC_FILE}")
        sys.exit(1)

    # Build command
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--clean"]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)

    print("Build complete!")
    print(f"Application located in: {DIST_DIR}")


def create_installer():
    """Create installer using Inno Setup (Windows only)."""
    if sys.platform != "win32":
        print("Installer creation is only supported on Windows.")
        return

    # Check if Inno Setup is available
    iscc_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if not os.path.exists(iscc_path):
        # Try common locations
        for path in [
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        ]:
            if os.path.exists(path):
                iscc_path = path
                break
        else:
            print("Inno Setup not found!")
            print("Install from: https://jrsoftware.org/isinfo.php")
            print("Then uncomment the installer section in build.spec")
            return

    # Create installer script
    installer_script = create_inno_script()
    script_path = BUILD_DIR / "installer.iss"

    BUILD_DIR.mkdir(exist_ok=True)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(installer_script)

    # Build installer
    print("Building installer...")
    cmd = [iscc_path, str(script_path)]
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print("Installer build failed!")
        return

    print("Installer created in: installer/")


def create_inno_script():
    """Create Inno Setup script."""
    return """[Setup]
AppId={{YOUR-GUID-HERE}
AppName=Text-to-Speech
AppVersion=1.0.0
AppPublisher=TTS App
DefaultDirName={autopf}\\Text-to-Speech
DefaultGroupName=Text-to-Speech
OutputDir=installer
OutputBaseFilename=setup_text_to_speech_1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\\TextToSpeech\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\\Text-to-Speech"; Filename: "{app}\\TextToSpeech.exe"
Name: "{autodesktop}\\Text-to-Speech"; Filename: "{app}\\TextToSpeech.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\\TextToSpeech.exe"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent
"""


def download_dependencies():
    """Download required dependencies."""
    print("Downloading dependencies...")

    # Install pip packages
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    print("Dependencies installed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Text-to-Speech application")
    parser.add_argument("--clean", action="store_true", help="Clean build directories")
    parser.add_argument("--installer", action="store_true", help="Create installer")
    parser.add_argument("--deps", action="store_true", help="Download dependencies")

    args = parser.parse_args()

    if args.clean:
        clean()
    elif args.installer:
        create_installer()
    elif args.deps:
        download_dependencies()
    else:
        build()
