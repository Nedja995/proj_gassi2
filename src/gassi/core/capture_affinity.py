"""SetWindowDisplayAffinity helper — hide overlay windows from OBS and game capture.

Windows-only. Applies WDA_EXCLUDEFROMCAPTURE (Win10 2004+, build 19041) to a
window HWND so the window is invisible to screen-capture tools and game anti-cheat
overlays that enumerate capture targets.

Failure modes:
  - Windows < build 19041: SetWindowDisplayAffinity exists but WDA_EXCLUDEFROMCAPTURE
    is not available — the call returns ERROR_INVALID_PARAMETER (87). Logged as
    WARNING and silently ignored.
  - pywin32 / ctypes not available: ImportError caught, logged as DEBUG.
  - Non-Windows platform: no-op, no warning.

Anti-cheat context:
  WDA_EXCLUDEFROMCAPTURE prevents the window pixels from appearing in capture
  streams (OBS, game bar, DirectX/GDI screen capture APIs). It does NOT hide the
  window from the window list (EnumWindows), process list, or OpenProcess scans.
  Combined with GASSI's pure CV approach (no memory reads, no code injection),
  this satisfies the typical screen-capture restriction clause in EULA anti-cheat
  policies for productivity overlays.

  AD-28 in docs/architecture.md.
"""

import ctypes
import logging
import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

logger = logging.getLogger(__name__)

# Win32 constants
_WDA_NONE = 0x00000000              # remove affinity — allow capture
_WDA_MONITOR = 0x00000001           # limit to same monitor session
_WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Win10 2004+: exclude from all capture APIs


def _set_affinity(hwnd: int, affinity_flag: int) -> bool:
    """Call SetWindowDisplayAffinity via ctypes. Returns True on success."""
    try:
        result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity_flag)
        if result == 0:
            err = ctypes.windll.kernel32.GetLastError()
            logger.warning(
                "SetWindowDisplayAffinity(hwnd=%d, flag=0x%x) failed — error %d "
                "(Win10 build 19041+ required for WDA_EXCLUDEFROMCAPTURE)",
                hwnd, affinity_flag, err,
            )
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("SetWindowDisplayAffinity unavailable: %s", exc)
        return False


def apply_capture_affinity(hwnd: int, hide: bool) -> bool:
    """Set or clear WDA_EXCLUDEFROMCAPTURE on a raw HWND.

    Args:
        hwnd: Win32 window handle (int).
        hide: True → exclude from capture. False → restore (WDA_NONE).

    Returns:
        True if the Win32 call succeeded, False otherwise.
        Always returns False on non-Windows platforms (no-op).
    """
    if platform.system() != "Windows":
        return False
    flag = _WDA_EXCLUDEFROMCAPTURE if hide else _WDA_NONE
    success = _set_affinity(hwnd, flag)
    if success:
        state = "hidden from capture" if hide else "capture allowed"
        logger.debug("SetWindowDisplayAffinity ok — hwnd=%d (%s)", hwnd, state)
    return success


def apply_capture_affinity_to_widget(widget: "tk.BaseWidget", hide: bool) -> bool:
    """Apply capture affinity to a tkinter widget using its winfo_id() HWND.

    Args:
        widget: Any tkinter widget (Tk root, Toplevel, etc.).
        hide:   True → exclude from capture. False → restore.

    Returns:
        True if successful. False on non-Windows or Win32 failure.
    """
    if platform.system() != "Windows":
        return False
    try:
        hwnd = int(widget.winfo_id())
        if not hwnd:
            logger.debug("apply_capture_affinity_to_widget: winfo_id() returned 0")
            return False
        return apply_capture_affinity(hwnd, hide)
    except Exception as exc:  # noqa: BLE001
        logger.debug("apply_capture_affinity_to_widget error: %s", exc)
        return False
