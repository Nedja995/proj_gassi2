"""MSS-based screen capture implementation.

Known platform limitations:
    Wayland: mss captures via XWayland — works for most Proton/Steam games.
             Pure Wayland apps (e.g. native Wayland compositor windows) are
             not capturable. A PipeWire/portal backend is deferred to vFuture.

    macOS:   macOS 10.15+ requires Screen Recording permission (System
             Preferences → Privacy & Security → Screen Recording). mss
             prompts for this automatically on first capture. If the user
             denies the permission, mss raises ScreenShotError. We catch
             that and surface a readable message instead of crashing (v0.9.8).
"""

import logging
import platform

import numpy as np
import mss
import mss.exception

logger = logging.getLogger(__name__)

_MACOS_SCREEN_RECORDING_MSG = (
    "Screen Recording permission required.\n"
    "Open System Preferences → Privacy & Security → Screen Recording "
    "and enable GASSI, then restart."
)


class MssCaptureBackend:
    """Screen capture using the mss library.

    Cross-platform (Windows/macOS/X11). Does not support pure Wayland —
    a separate PipeWire-based backend is needed for that (vFuture).
    """

    def __init__(self) -> None:
        self._sct = mss.mss()

    def grab(self, region: tuple[int, int, int, int] | None = None) -> np.ndarray:
        """Capture a screen region as a numpy BGR array.

        Raises:
            RuntimeError: on macOS when Screen Recording permission is denied.
        """
        if region is not None:
            x, y, w, h = region
            monitor = {"left": x, "top": y, "width": w, "height": h}
        else:
            monitor = self._sct.monitors[1]  # primary monitor

        try:
            screenshot = self._sct.grab(monitor)
        except mss.exception.ScreenShotError as exc:
            # macOS: Screen Recording permission denied or revoked.
            # Convert to a readable RuntimeError so the overlay can display
            # the message instead of crashing with a raw mss exception.
            if platform.system() == "Darwin":
                logger.error(
                    "mss ScreenShotError on macOS — likely Screen Recording permission denied: %s",
                    exc,
                )
                raise RuntimeError(_MACOS_SCREEN_RECORDING_MSG) from exc
            raise

        # mss returns BGRA; drop alpha channel -> BGR
        frame = np.array(screenshot, dtype=np.uint8)
        return frame[:, :, :3]

    def __del__(self) -> None:
        self._sct.close()
