"""Capture region providers — how we know where the game window is."""

import tkinter as tk


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
