# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Text-to-Speech application.
Build command: pyinstaller build.spec
"""

block_cipher = None

# Application name — must match installer.iss
app_name = 'TTS_Lite'

# Main script
main_script = 'main.py'

# Data files to include
datas = [
    ('resources/styles/*.qss', 'resources/styles'),
    ('resources/translations/*', 'resources/translations'),
    ('resources/icons/*', 'resources/icons'),
]

# Hidden imports
hiddenimports = [
    'PySide6',
    'PySide6.QtWidgets',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'numpy',
    'sounddevice',
    'piper',
    'pydub',
    'scipy',
    'scipy.signal',
    'striprtf',
    'requests',
    'edge_tts',
    'supertonic',
    'imageio_ffmpeg',
]

# Excluded modules to speed up build
excludes = [
    'torch', 'torchvision', 'torchaudio',
    'transformers', 'tokenizers',
    'sklearn', 'sklearn.',
    'matplotlib', 'matplotlib.',
    'pandas', 'pandas.',
    'PIL', 'PIL.',
    'tkinter', 'tkinter.',
    'pygame', 'pygame.',
    'librosa', 'librosa.',
    'numba', 'numba.',
    'llvmlite',
    'jinja2', 'jinja2.',
    'IPython', 'IPython.',
    'notebook', 'notebook.',
    'ipykernel', 'ipykernel.',
    'pytest', 'pytest.',
    'unittest',
    'xmlrpc',
    'pydoc',
    'pdb', 'pdb.',
    'profile', 'cProfile',
    'distutils', 'distutils.',
    'setuptools', 'setuptools.',
    'pip', 'pip.',
    'conda', 'conda.',
]

a = Analysis(
    [main_script],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)
