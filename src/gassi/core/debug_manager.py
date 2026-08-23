"""Debug utilities — frame persistence, debug directory management.

Provides a single DebugManager instance for saving captured frames
to disk and resolving the debug output directory.

Debug frames are saved to: <config_dir>/debug_frames/
  e.g. %LOCALAPPDATA%\\gassi\\debug_frames\\frame_20260823_153045_123.png
"""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from gassi.core.settings_manager import _get_config_dir  # shared config dir

logger = logging.getLogger(__name__)

_DEBUG_FRAMES_SUBDIR = "debug_frames"
_MAX_SAVED_FRAMES = 50  # auto-prune oldest when exceeded


def _get_debug_frames_dir() -> Path:
    """Return (and create) the debug frames output directory."""
    debug_dir = _get_config_dir() / _DEBUG_FRAMES_SUBDIR
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir


def _prune_old_frames(debug_dir: Path) -> None:
    """Remove oldest frames if count exceeds _MAX_SAVED_FRAMES."""
    frames = sorted(debug_dir.glob("frame_*.png"), key=lambda p: p.stat().st_mtime)
    excess = len(frames) - _MAX_SAVED_FRAMES
    if excess > 0:
        for old_frame in frames[:excess]:
            try:
                old_frame.unlink()
            except OSError:
                pass


class DebugManager:
    """Handles debug frame persistence for captured screen regions."""

    def __init__(self) -> None:
        self._last_frame: np.ndarray | None = None
        self._last_frame_label: str = ""

    def store_frame(self, frame: np.ndarray, label: str = "") -> None:
        """Store the latest captured frame for potential debug save.

        Args:
            frame: BGR numpy array from capture backend.
            label: short descriptor (e.g. "advisor_ocr", "placement").
        """
        self._last_frame = frame
        self._last_frame_label = label

    def save_last_frame(self) -> Path | None:
        """Save the last stored frame to the debug frames directory.

        Returns:
            Path to the saved PNG, or None if no frame is stored.
        """
        if self._last_frame is None:
            logger.warning("save_last_frame called but no frame stored yet")
            return None

        debug_dir = _get_debug_frames_dir()
        _prune_old_frames(debug_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        label_part = f"_{self._last_frame_label}" if self._last_frame_label else ""
        filename = f"frame_{timestamp}{label_part}.png"
        output_path = debug_dir / filename

        try:
            rgb = self._last_frame[:, :, ::-1]  # BGR → RGB
            image = Image.fromarray(rgb)
            image.save(output_path, format="PNG")
            logger.info("Debug frame saved: %s", output_path)
            return output_path
        except OSError as exc:
            logger.error("Failed to save debug frame: %s", exc)
            return None

    def has_frame(self) -> bool:
        """Return True if a frame is available to save."""
        return self._last_frame is not None

    @property
    def last_frame_label(self) -> str:
        return self._last_frame_label

    @staticmethod
    def get_debug_dir() -> Path:
        """Return the debug frames directory path (for display in UI)."""
        return _get_debug_frames_dir()
