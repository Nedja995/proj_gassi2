"""MSS-based screen capture implementation."""

import numpy as np
import mss


class MssCaptureBackend:
    """Screen capture using the mss library.

    Cross-platform (Windows/macOS/X11). Does not support Wayland —
    a separate PipeWire-based backend is needed for that (v2).
    """

    def __init__(self) -> None:
        self._sct = mss.mss()

    def grab(self, region: tuple[int, int, int, int] | None = None) -> np.ndarray:
        """Capture a screen region as a numpy BGR array."""
        if region is not None:
            x, y, w, h = region
            monitor = {"left": x, "top": y, "width": w, "height": h}
        else:
            monitor = self._sct.monitors[1]  # primary monitor

        screenshot = self._sct.grab(monitor)
        # mss returns BGRA; drop alpha channel -> BGR
        frame = np.array(screenshot, dtype=np.uint8)
        return frame[:, :, :3]

    def __del__(self) -> None:
        self._sct.close()
