"""Persistent settings manager — loads/saves user config to JSON file.

Bridges the gap between pydantic-settings (read-only from env) and
runtime user changes from the settings dialog. Settings are saved
to a JSON file in the user's app data directory.

Write strategy:
    All public save functions use _write_atomic() which writes to a
    .tmp file then renames it, preventing partial writes from corrupting
    the settings file if the process is killed mid-save.
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


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write JSON to a .tmp file then rename — atomic on all platforms.

    Prevents a corrupted settings.json if the process is killed mid-write.
    On Windows, replace() is atomic since Python 3.3.
    """
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(path)
    except OSError as exc:
        logger.error("Failed to write settings to %s: %s", path, exc)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


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
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load settings from %s: %s", path, exc)
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    """Save settings dict to the JSON config file."""
    path = _get_config_path()
    _write_atomic(path, settings)
    logger.info("Settings saved to %s", path)


def save_window_geometry(geometry: str) -> None:
    """Persist window geometry string.

    Merges into existing settings rather than overwriting, so geometry
    saves don't clobber settings changed in the same session.
    """
    data = load_saved_settings()
    data["_window_geometry"] = geometry
    _write_atomic(_get_config_path(), data)


def load_window_geometry() -> str | None:
    """Load saved window geometry string."""
    return load_saved_settings().get("_window_geometry")


def save_prompt_history(history: list[str]) -> None:
    """Persist the last N placement prompt queries."""
    data = load_saved_settings()
    data["_prompt_history"] = history
    _write_atomic(_get_config_path(), data)


def load_prompt_history() -> list[str]:
    """Load persisted placement prompt history."""
    return load_saved_settings().get("_prompt_history", [])
