# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for GASSI — --onedir build.

Build command:
    uv run pyinstaller gassi.spec

Output:
    dist/gassi/gassi.exe   (launcher)
    dist/gassi/_internal/  (Python runtime + dependencies)
    dist/gassi/game_packs/ (bundled game data)

The spec bundles game_packs/ into the root of the output folder
so that get_base_dir() (which resolves to sys._MEIPASS in frozen mode)
finds them at <base>/game_packs/.
"""

import os
import sys
from pathlib import Path

# Project root — where this spec file lives
_PROJECT_ROOT = Path(SPECPATH)
_SRC = _PROJECT_ROOT / "src"

block_cipher = None

a = Analysis(
    [str(_SRC / "gassi" / "main.py")],
    pathex=[str(_SRC)],
    binaries=[],
    datas=[
        # game_packs/ tree — manifest, prompts, knowledge, rag collections
        (str(_PROJECT_ROOT / "game_packs"), "game_packs"),
        # rapidocr_onnxruntime config + model files
        (os.path.join(os.path.dirname(__import__('rapidocr_onnxruntime').__file__), 'config.yaml'),
         'rapidocr_onnxruntime'),
        (os.path.join(os.path.dirname(__import__('rapidocr_onnxruntime').__file__), 'models'),
         'rapidocr_onnxruntime/models'),
    ],
    hiddenimports=[
        # --- core deps (always present) ---
        "pydantic",
        "pydantic_settings",
        "keyring",
        "keyring.backends",
        "keyring.backends.Windows",
        "mss",
        "mss.windows",
        "PIL",
        "cv2",
        "rapidocr_onnxruntime",
        "onnxruntime",
        "numpy",
        "yaml",
        "pynput",
        "pynput.keyboard",
        "pynput.keyboard._win32",
        "google",
        "google.genai",
        # --- optional: claude ---
        "anthropic",
        # --- optional: rag ---
        "chromadb",
        # --- tkinter (usually bundled, but be explicit) ---
        "tkinter",
        "tkinter.ttk",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused packages that may get pulled transitively
        "torch",
        "torchvision",
        "torchaudio",
        "tensorflow",
        "transformers",
        "sentence_transformers",
        "matplotlib",
        "scipy",
        "pandas",
        "jupyter",
        "notebook",
        "IPython",
    ],
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
    name="gassi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # keep console for now — shows logs during beta
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="gassi",
)
