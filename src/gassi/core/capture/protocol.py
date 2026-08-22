"""Capture backend protocol — interface for screen capture providers."""

from typing import Protocol

import numpy as np


class CaptureBackend(Protocol):
    """Abstract interface for screen region capture.

    v1: MssCaptureBackend (Windows/macOS/X11).
    Future: PipeWire/portal backend for Wayland.
    """

    def grab(self, region: tuple[int, int, int, int] | None = None) -> np.ndarray:
        """Capture a screen region and return as numpy BGR array.

        Args:
            region: (x, y, width, height) in screen pixels.
                    None captures the primary monitor.

        Returns:
            numpy array in BGR format (OpenCV convention).
        """
        ...


class CaptureRegionProvider(Protocol):
    """Provides the capture rectangle for the game window.

    v1: OverlayAnchoredRegionProvider — derives rect from overlay geometry.
    v2: NativeWindowRegionProvider — per-OS window handle lookup.
    """

    def get_capture_rect(self) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) of the game window in screen coords."""
        ...
