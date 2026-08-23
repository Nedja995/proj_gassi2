"""Capture region providers — how we know where the game window is."""

import tkinter as tk
import mss


class OverlayAnchoredRegionProvider:
    """v1: derives capture rect from the overlay window's own screen geometry.

    User manually positions/resizes the overlay to cover the game window.
    The overlay's geometry IS the capture boundary.

    v2: NativeWindowRegionProvider will implement the same Protocol
    using per-OS window handle lookup (pywin32/pyobjc/Xlib).
    """

    def __init__(self, overlay: tk.Tk) -> None:
        self._overlay = overlay

    def get_capture_rect(self) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) from the overlay's current geometry."""
        return (
            self._overlay.winfo_x(),
            self._overlay.winfo_y(),
            self._overlay.winfo_width(),
            self._overlay.winfo_height(),
        )

    def get_monitor_rect(self) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) of the primary monitor.

        Used for HUD region resolution — fractional coordinates in
        manifest/calibration are relative to the full screen, not the overlay.
        """
        with mss.mss() as sct:
            m = sct.monitors[1]  # primary monitor
            return (m["left"], m["top"], m["width"], m["height"])
