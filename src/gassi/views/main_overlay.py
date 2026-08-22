"""Main overlay window — always-on-top, semi-transparent, toggleable click-through.

Platform-specific transparency and click-through are handled via native
hooks. Click-through is OFF by default so the user can position/resize
the window, then toggled on via hotkey or UI button during gameplay.
"""

import logging
import platform
import tkinter as tk
from tkinter import ttk

from gassi.core.overlay.overlay_canvas import OverlayCanvas

logger = logging.getLogger(__name__)

_DEFAULT_WIDTH = 420
_DEFAULT_HEIGHT = 320
_DEFAULT_ALPHA = 0.88
_BG_COLOR = "#1a1a2e"
_ACCENT_COLOR = "#00ff88"
_HEADER_COLOR = "#16213e"
_FOOTER_COLOR = "#16213e"


class MainOverlay(tk.Tk):
    """Root overlay window — hosts the OverlayCanvas and control bar."""

    def __init__(self) -> None:
        super().__init__()

        self._click_through_active = False
        self._system = platform.system()

        self.title("GASSI")
        self.geometry(f"{_DEFAULT_WIDTH}x{_DEFAULT_HEIGHT}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", _DEFAULT_ALPHA)
        self.configure(bg=_BG_COLOR)
        self.minsize(300, 200)

        # ── header bar ────────────────────────────────────────────────
        self._header = tk.Frame(self, bg=_HEADER_COLOR, height=32, cursor="fleur")
        self._header.pack(fill=tk.X, side=tk.TOP)
        self._header.pack_propagate(False)

        title_label = tk.Label(
            self._header,
            text="⬡ GASSI",
            bg=_HEADER_COLOR,
            fg=_ACCENT_COLOR,
            font=("Consolas", 10, "bold"),
        )
        title_label.pack(side=tk.LEFT, padx=8)

        self._status_label = tk.Label(
            self._header,
            text="IDLE",
            bg=_HEADER_COLOR,
            fg="#888888",
            font=("Consolas", 9),
        )
        self._status_label.pack(side=tk.LEFT, padx=(0, 10))

        self._lock_button = tk.Button(
            self._header,
            text="🔓",
            bg=_HEADER_COLOR,
            fg="#cccccc",
            font=("Consolas", 10),
            bd=0,
            activebackground=_HEADER_COLOR,
            command=self.toggle_click_through,
            cursor="hand2",
        )
        self._lock_button.pack(side=tk.RIGHT, padx=5)

        # make header draggable
        self._header.bind("<Button-1>", self._start_drag)
        self._header.bind("<B1-Motion>", self._on_drag)
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._on_drag)

        # ── footer bar (hotkey hints + cooldown) ──────────────────────
        self._footer = tk.Frame(self, bg=_FOOTER_COLOR, height=24)
        self._footer.pack(fill=tk.X, side=tk.BOTTOM)
        self._footer.pack_propagate(False)

        self._hints_label = tk.Label(
            self._footer,
            text="F1: Advisor  |  F2: Placement  |  F3: Lock",
            bg=_FOOTER_COLOR,
            fg="#555555",
            font=("Consolas", 8),
        )
        self._hints_label.pack(side=tk.LEFT, padx=8)

        self._cooldown_label = tk.Label(
            self._footer,
            text="",
            bg=_FOOTER_COLOR,
            fg="#ffaa00",
            font=("Consolas", 8, "bold"),
        )
        self._cooldown_label.pack(side=tk.RIGHT, padx=8)

        # ── main drawing surface ──────────────────────────────────────
        self.canvas = OverlayCanvas(self, bg=_BG_COLOR)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._drag_offset_x = 0
        self._drag_offset_y = 0

    # ── status display ────────────────────────────────────────────────

    def update_status(self, mode: str, source: str = "") -> None:
        """Update the header status label."""
        text = mode.upper()
        if source:
            text += f" [{source}]"
        self._status_label.config(
            text=text,
            fg=_ACCENT_COLOR if mode.lower() not in ("idle", "") else "#888888",
        )

    def update_cooldown(self, text: str) -> None:
        """Update the footer cooldown timer text."""
        self._cooldown_label.config(text=text)

    # ── click-through toggle ──────────────────────────────────────────

    def toggle_click_through(self) -> None:
        """Toggle click-through mode on/off."""
        if self._click_through_active:
            self._disable_click_through()
        else:
            self._enable_click_through()

    def _enable_click_through(self) -> None:
        """Make the canvas area pass-through; header stays interactive."""
        self._click_through_active = True
        self._lock_button.config(text="🔒")
        self.attributes("-alpha", 0.65)

        if self._system == "Windows":
            self._set_windows_click_through(True)
        elif self._system == "Darwin":
            self._set_macos_click_through(True)

        logger.info("Click-through enabled")

    def _disable_click_through(self) -> None:
        """Restore normal window interaction."""
        self._click_through_active = False
        self._lock_button.config(text="🔓")
        self.attributes("-alpha", _DEFAULT_ALPHA)

        if self._system == "Windows":
            self._set_windows_click_through(False)
        elif self._system == "Darwin":
            self._set_macos_click_through(False)

        logger.info("Click-through disabled")

    def _set_windows_click_through(self, enabled: bool) -> None:
        """Windows: toggle WS_EX_TRANSPARENT via pywin32."""
        try:
            import win32con  # type: ignore[import-untyped]
            import win32gui  # type: ignore[import-untyped]

            hwnd = self.winfo_id()
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

            if enabled:
                ex_style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            else:
                ex_style &= ~win32con.WS_EX_TRANSPARENT

            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        except ImportError:
            logger.debug("pywin32 not installed — click-through unavailable")

    def _set_macos_click_through(self, enabled: bool) -> None:
        """macOS: toggle setIgnoresMouseEvents_ via pyobjc."""
        try:
            from AppKit import NSApp  # type: ignore[import-untyped]

            window = NSApp.windows()[0]
            window.setIgnoresMouseEvents_(enabled)
        except ImportError:
            logger.debug("pyobjc not installed — click-through unavailable")

    # ── window dragging ───────────────────────────────────────────────

    def _start_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag_offset_x = event.x
        self._drag_offset_y = event.y

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        x = self.winfo_x() + event.x - self._drag_offset_x
        y = self.winfo_y() + event.y - self._drag_offset_y
        self.geometry(f"+{x}+{y}")
