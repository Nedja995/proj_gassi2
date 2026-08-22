"""Persistent settings manager — loads/saves user config to JSON file.

Bridges the gap between pydantic-settings (read-only from env) and
runtime user changes from the settings dialog. Settings are saved
to a JSON file in the user's app data directory.
"""

import json
import logging
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_APP_NAME = "gassi"


def _get_config_dir() -> Path:
    """Get the platform-appropriate config directory."""
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    config_dir = base / _APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _get_config_path() -> Path:
    return _get_config_dir() / "settings.json"


def load_saved_settings() -> dict[str, Any]:
    """Load settings from the JSON config file. Returns empty dict if none."""
    path = _get_config_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded settings from %s", path)
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load settings from %s: %s", path, e)
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    """Save settings dict to the JSON config file."""
    path = _get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        logger.info("Settings saved to %s", path)
    except OSError as e:
        logger.error("Failed to save settings to %s: %s", path, e)


def save_window_geometry(geometry: str) -> None:
    """Save window geometry string separately (frequent updates)."""
    data = load_saved_settings()
    data["_window_geometry"] = geometry
    save_settings(data)


def load_window_geometry() -> str | None:
    """Load saved window geometry string."""
    data = load_saved_settings()
    return data.get("_window_geometry")
