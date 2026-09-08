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

# Data files to include — include ffmpeg binary for imageio_ffmpeg
from PyInstaller.utils.hooks import collect_data_files, collect_all
try:
    _ffmpeg_datas, _ffmpeg_binaries, _ffmpeg_hidden = collect_all('imageio_ffmpeg')
except Exception:
    _ffmpeg_datas, _ffmpeg_binaries, _ffmpeg_hidden = [], [], []
try:
    _onnx_datas, _onnx_binaries, _onnx_hidden = collect_all('onnxruntime')
except Exception:
    _onnx_datas, _onnx_binaries, _onnx_hidden = [], [], []

datas = [
    ('resources/styles/*.qss', 'resources/styles'),
    ('resources/translations/*', 'resources/translations'),
    ('resources/icons/*', 'resources/icons'),
] + _ffmpeg_datas + _onnx_datas
binaries = _ffmpeg_binaries + _onnx_binaries

# Hidden imports — must include runtime deps that PyInstaller misses via static analysis
hiddenimports = [
    'PySide6',
    'PySide6.QtWidgets',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'numpy',
    'sounddevice',
    'soundfile',
    'piper',
    'onnxruntime',
    'pydub',
    'scipy',
    'scipy.signal',
    'striprtf',
    'requests',
    'edge_tts',
    'supertonic',
    'imageio_ffmpeg',
    'unittest',  # supertonic imports unittest/pydoc at runtime
    'pydoc',
    'xmlrpc',
    'xmlrpc.client',
] + _ffmpeg_hidden + _onnx_hidden

# Excluded modules to speed up build (do NOT exclude unittest/pydoc/xmlrpc — supertonic needs them)
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
    binaries=binaries,
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
