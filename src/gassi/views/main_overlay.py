"""Main overlay window — always-on-top, semi-transparent, click-through capable.

Platform-specific transparency and click-through are handled via native
hooks in _apply_platform_tweaks(). The window itself is a standard tkinter
Toplevel with the OverlayCanvas as its primary drawing surface.
"""

import logging
import platform
import tkinter as tk

from gassi.core.overlay.overlay_canvas import OverlayCanvas

logger = logging.getLogger(__name__)

_DEFAULT_WIDTH = 400
_DEFAULT_HEIGHT = 300
_DEFAULT_ALPHA = 0.85


class MainOverlay(tk.Tk):
    """Root overlay window — hosts the OverlayCanvas and control widgets."""

    def __init__(self) -> None:
        super().__init__()

        self.title("GASSI")
        self.geometry(f"{_DEFAULT_WIDTH}x{_DEFAULT_HEIGHT}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", _DEFAULT_ALPHA)
        self.configure(bg="black")

        # main drawing surface
        self.canvas = OverlayCanvas(self)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._apply_platform_tweaks()

    def _apply_platform_tweaks(self) -> None:
        """Apply OS-specific transparency and click-through settings."""
        system = platform.system()

        if system == "Windows":
            self._apply_windows_tweaks()
        elif system == "Darwin":
            self._apply_macos_tweaks()
        elif system == "Linux":
            self._apply_linux_tweaks()
        else:
            logger.warning("Unknown platform '%s' — no overlay tweaks applied", system)

    def _apply_windows_tweaks(self) -> None:
        """Windows: transparent color key + layered window attributes.

        Full click-through (WS_EX_TRANSPARENT) requires pywin32 and is
        applied conditionally — if pywin32 is not installed, the overlay
        is still usable but intercepts mouse events.
        """
        self.attributes("-transparentcolor", "black")
        try:
            import win32con  # type: ignore[import-untyped]
            import win32gui  # type: ignore[import-untyped]

            hwnd = self.winfo_id()
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            logger.info("Windows click-through enabled via pywin32")
        except ImportError:
            logger.info("pywin32 not installed — click-through disabled")

    def _apply_macos_tweaks(self) -> None:
        """macOS: requires Screen Recording permission for mss capture.

        Click-through via pyobjc NSWindow.setIgnoresMouseEvents_ if available.
        """
        try:
            from AppKit import NSApp  # type: ignore[import-untyped]

            window = NSApp.windows()[0]
            window.setIgnoresMouseEvents_(True)
            window.setLevel_(3)  # NSFloatingWindowLevel
            logger.info("macOS click-through enabled via pyobjc")
        except ImportError:
            logger.info("pyobjc not installed — click-through disabled")

    def _apply_linux_tweaks(self) -> None:
        """Linux/X11: basic transparency. Wayland is a known gap (v2)."""
        # X11 compositors (picom, mutter) handle alpha via -alpha attribute
        # already set in __init__. Click-through requires python-xlib (v2).
        logger.info("Linux overlay — X11 alpha via compositor, click-through deferred")
