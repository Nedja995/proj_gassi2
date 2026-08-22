"""Global hotkey manager using pynput.

Registers system-wide hotkeys that work while the game window has focus.
macOS: requires Accessibility permission.
Linux: may require input-group membership on some distros.
"""

import logging
from collections.abc import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Register and manage global hotkeys via pynput."""

    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: keyboard.GlobalHotKeys | None = None

    def register(self, hotkey_str: str, callback: Callable[[], None]) -> None:
        """Register a hotkey binding.

        Args:
            hotkey_str: pynput hotkey string, e.g. "<f1>", "<shift>+<f1>"
            callback: function to call when hotkey is pressed.
        """
        self._hotkeys[hotkey_str] = callback
        logger.info("Registered hotkey: %s", hotkey_str)

    def start(self) -> None:
        """Start listening for registered hotkeys in a background thread."""
        if not self._hotkeys:
            logger.warning("No hotkeys registered — listener not started")
            return

        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.daemon = True
        self._listener.start()
        logger.info("Hotkey listener started (%d bindings)", len(self._hotkeys))

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            logger.info("Hotkey listener stopped")
