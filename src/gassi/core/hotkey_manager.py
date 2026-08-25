"""Global hotkey manager using pynput.

Registers system-wide hotkeys that work while the game window has focus.
macOS: requires Accessibility permission.
Linux: may require input-group membership on some distros.
"""

import logging
import re
from collections.abc import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)

# pynput modifier-only keys that cannot stand alone as a hotkey trigger
_MODIFIER_ONLY_RE = re.compile(
    r"^(<shift>|<ctrl>|<alt>|<cmd>|<super>)(\+(<shift>|<ctrl>|<alt>|<cmd>|<super>))*$"
)


class HotkeyManager:
    """Register and manage global hotkeys via pynput."""

    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: keyboard.GlobalHotKeys | None = None

    def register(self, hotkey_str: str, callback: Callable[[], None]) -> None:
        """Register a hotkey binding.

        Args:
            hotkey_str: pynput hotkey string, e.g. "<f1>", "<alt>+8"
            callback: function to call when hotkey is pressed.

        Skips registration with a warning if the hotkey string is
        modifier-only (e.g. "<alt>") or clearly malformed — prevents
        Alt-alone triggering the advisor when settings.json contains
        a legacy broken format like "<alt>+<8>" from pre-v0.5.7.
        """
        stripped = hotkey_str.strip()
        if not stripped:
            logger.warning("Skipping empty hotkey string")
            return

        if _MODIFIER_ONLY_RE.match(stripped):
            logger.warning(
                "Skipping modifier-only hotkey '%s' — no trigger key. "
                "Re-bind this hotkey in Settings to fix.",
                stripped,
            )
            return

        self._hotkeys[stripped] = callback
        logger.info("Registered hotkey: %s", stripped)

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
