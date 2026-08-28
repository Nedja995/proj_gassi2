"""Resolve the project base directory — handles both dev and PyInstaller frozen modes.

Under normal Python execution:
    base_dir = project root (where pyproject.toml lives)

Under PyInstaller --onedir:
    base_dir = sys._MEIPASS (the extracted bundle directory)
    game_packs/ and docs/ are expected inside _MEIPASS via datas in gassi.spec.
"""

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Return the base directory for resolving bundled data (game_packs/, docs/).

    In dev mode: project root (3 parents up from this file: src/gassi/core/).
    In frozen mode: sys._MEIPASS (PyInstaller's temp extraction dir).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # dev mode: this file is at src/gassi/core/paths.py
    # project root is 3 levels up: core -> gassi -> src -> root
    return Path(__file__).resolve().parents[3]
