"""NativeWindowRegionProvider — per-OS game window detection.

Replaces OverlayAnchoredRegionProvider for users who enable
"Auto-detect game window" in Settings. Finds the game window by title
pattern (and optionally window class on Windows) so the overlay does not
need to be manually positioned over the game.

Platform support (v0.9.7):
    Windows: win32gui.FindWindow / EnumWindows — pywin32, already in stack.
    macOS:   NSWorkspace stub — pyobjc not required; fails open to overlay rect.
    Linux:   no-op — falls open to overlay rect.

Detection strategy:
    1. If window_class is set in the manifest AND we are on Windows,
       call FindWindow(class, None) first — exact class match, zero false positives.
    2. Fall through to title-pattern substring scan via EnumWindows so a
       partial title like "Timberborn" matches "Timberborn (0.6.4.0)" etc.
    3. On any error or platform, return the overlay rect unchanged (fail open).

This provider satisfies the CaptureRegionProvider Protocol — it exposes
both get_capture_rect() and get_monitor_rect() so it is a drop-in
replacement for OverlayAnchoredRegionProvider anywhere in the codebase.
"""

import logging
import platform
import tkinter as tk

import mss

logger = logging.getLogger(__name__)


class NativeWindowRegionProvider:
    """Locate the game window via OS APIs and return its screen rect.

    Args:
        overlay: The main Tk root window — used as fallback rect source and
                 to resolve the primary monitor dimensions.
        title_pattern: Substring to match against window titles (case-insensitive).
                       Comes from GamePackManifest.window_title_pattern.
        window_class: Optional Win32 window class name for faster/safer lookup
                      on Windows. Comes from GamePackManifest.window_class.
                      Ignored on non-Windows platforms.

    Falls back silently to overlay geometry when:
        - The OS is not Windows (macOS / Linux paths not yet implemented).
        - pywin32 is not installed.
        - No window matching the title_pattern is found.
        - Any unexpected Win32 error occurs.
    """

    def __init__(
        self,
        overlay: tk.Tk,
        title_pattern: str,
        window_class: str | None = None,
    ) -> None:
        self._overlay = overlay
        self._title_pattern = title_pattern.lower() if title_pattern else ""
        self._window_class = window_class  # Win32 class name, may be None

    # ── CaptureRegionProvider Protocol ────────────────────────────────

    def get_capture_rect(self) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) of the game window in screen pixels.

        Tries OS-level window detection first; falls back to overlay geometry.
        """
        detected = self._find_game_window()
        if detected is not None:
            return detected

        # fallback — overlay geometry (same as OverlayAnchoredRegionProvider)
        return (
            self._overlay.winfo_x(),
            self._overlay.winfo_y(),
            self._overlay.winfo_width(),
            self._overlay.winfo_height(),
        )

    def get_monitor_rect(self) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) of the primary monitor.

        Identical to OverlayAnchoredRegionProvider.get_monitor_rect().
        HUD region fractions are always relative to the full screen.
        """
        with mss.mss() as sct:
            m = sct.monitors[1]  # primary monitor
            return (m["left"], m["top"], m["width"], m["height"])

    # ── internal detection ─────────────────────────────────────────────

    def _find_game_window(self) -> tuple[int, int, int, int] | None:
        """Return (x, y, w, h) for the best-matching game window, or None."""
        current_os = platform.system()

        if current_os == "Windows":
            return self._find_window_windows()
        if current_os == "Darwin":
            return self._find_window_macos()
        # Linux: no implementation yet — fail open
        return None

    def _find_window_windows(self) -> tuple[int, int, int, int] | None:
        """Windows implementation using win32gui.

        Strategy:
            1. If window_class is set: try FindWindow(class, None) — exact class match.
            2. Fall through to EnumWindows title-pattern substring scan.
            3. Return None on any error or no match.
        """
        try:
            import win32gui  # type: ignore[import-untyped]
        except ImportError:
            logger.debug("pywin32 not available — NativeWindowRegionProvider falls back to overlay rect")
            return None

        if not self._title_pattern:
            return None

        # --- strategy 1: class-based lookup (Windows only, fastest) ---
        if self._window_class:
            try:
                hwnd = win32gui.FindWindow(self._window_class, None)
                if hwnd:
                    rect = self._hwnd_to_rect(win32gui, hwnd)
                    if rect is not None:
                        logger.debug(
                            "NativeWindow: found '%s' via class '%s' → %s",
                            self._title_pattern, self._window_class, rect,
                        )
                        return rect
            except Exception as exc:  # noqa: BLE001
                logger.debug("FindWindow(class) failed: %s", exc)

        # --- strategy 2: EnumWindows title scan ---
        _found_rect: list[tuple[int, int, int, int]] = []

        def _enum_callback(hwnd: int, _lparam: object) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if self._title_pattern in title.lower():
                rect = self._hwnd_to_rect(win32gui, hwnd)
                if rect is not None:
                    _found_rect.append(rect)
                    return False  # stop enumeration on first match
            return True

        try:
            win32gui.EnumWindows(_enum_callback, None)
        except Exception as exc:  # noqa: BLE001
            # EnumWindows raises the exception returned by the callback's False;
            # that is expected behaviour — the rect is already captured.
            if not _found_rect:
                logger.debug("EnumWindows error (no match): %s", exc)

        if _found_rect:
            rect = _found_rect[0]
            logger.debug(
                "NativeWindow: found '%s' via title scan → %s",
                self._title_pattern, rect,
            )
            return rect

        logger.debug(
            "NativeWindow: no visible window matched title pattern '%s'",
            self._title_pattern,
        )
        return None

    def _find_window_macos(self) -> tuple[int, int, int, int] | None:
        """macOS stub — pyobjc / Quartz not yet implemented.

        Returns None (fail open) so the overlay rect fallback is used.
        Tracked in TODO for v0.9.8.
        """
        logger.debug("NativeWindow: macOS native detection not yet implemented — using overlay rect")
        return None

    @staticmethod
    def _hwnd_to_rect(
        win32gui: object,
        hwnd: int,
    ) -> tuple[int, int, int, int] | None:
        """Convert a Win32 HWND to (x, y, w, h) client rect.

        Uses GetClientRect projected to screen via ClientToScreen so we get
        the drawable game area, not the window frame (titlebar / borders).
        Returns None if the HWND is invalid or rect is degenerate.
        """
        try:
            # GetClientRect returns (left=0, top=0, right=w, bottom=h)
            client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)  # type: ignore[attr-defined]
            client_w = client_right - client_left
            client_h = client_bottom - client_top

            if client_w <= 0 or client_h <= 0:
                return None

            # Map client (0, 0) to screen coordinates
            import ctypes
            _pt = ctypes.wintypes.POINT(0, 0)
            ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(_pt))
            screen_x = _pt.x
            screen_y = _pt.y

            return (screen_x, screen_y, client_w, client_h)
        except Exception as exc:  # noqa: BLE001
            logger.debug("_hwnd_to_rect failed for hwnd %s: %s", hwnd, exc)
            return None
