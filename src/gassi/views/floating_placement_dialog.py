"""Floating placement dialog — centered Toplevel for F2 placement when overlay is offscreen.

Shown when:
  - The main overlay is slid offscreen (`_offscreen = True`)
  - F2 hotkey fires (or placement is triggered via `_open_placement` in main.py)

Design:
  - Centered on the primary monitor, vertical center (35% from top)
  - Semi-transparent, always-on-top, themed
  - Larger than the inline PlacementInputStrip for comfortable keyboard use
  - Combobox pre-populated with history + quick-prompts (same data as strip)
  - Full keyboard focus: Enter submits, Escape dismisses
  - Not click-through — user actively types here

Hide/show:
  - Uses withdraw() / deiconify() — same pattern as FloatingAdviceWindow.
    No Win32 region tricks needed; no style bits to preserve.
    HWND recreation on withdraw() is acceptable here.

Lifecycle:
  - Created once at startup by MainOverlay.__init__ (alongside _floating_advice).
  - show() called by MainOverlay.show_floating_placement_dialog().
  - destroy() called by MainOverlay._on_close_click().

on_submit callback:
  - Supplied at show() time — always viewmodel.trigger_placement.
  - Dialog hides itself before calling on_submit so the overlay does not
    capture the dialog in the placement screenshot.
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable

from gassi.core.theme.theme import Theme

logger = logging.getLogger(__name__)

_WIN_WIDTH_FRACTION = 0.40   # 40% of screen width
_WIN_HEIGHT_FRACTION = 0.18  # 18% of screen height — input-only, no advice body
_WIN_MIN_WIDTH = 400
_WIN_MIN_HEIGHT = 120
_WIN_ALPHA = 0.95
_WIN_Y_FRACTION = 0.35       # vertical center — below advice window (0.08), no overlap


class FloatingPlacementDialog:
    """Centered Toplevel for placement queries when the main overlay is offscreen.

    Lifecycle is managed by MainOverlay — created once at startup, shown/hidden
    on demand. Never destroyed until app close.
    """

    def __init__(self, parent: tk.Tk, theme: Theme) -> None:
        self._parent = parent
        self._theme = theme
        self._toplevel: tk.Toplevel | None = None
        self._combo: ttk.Combobox | None = None
        self._combo_var: tk.StringVar | None = None
        self._on_submit: Callable[[str], None] | None = None

    # ── public API ────────────────────────────────────────────────────

    def show(
        self,
        suggestions: list[str],
        on_submit: Callable[[str], None],
    ) -> None:
        """Display the dialog with pre-populated suggestions.

        Args:
            suggestions: Ordered list of prompt suggestions (history first,
                then quick-prompts). Shown as combobox dropdown.
            on_submit: Callback invoked with the trimmed prompt string.
                Always viewmodel.trigger_placement in practice.
        """
        self._on_submit = on_submit

        if self._toplevel is None or not self._toplevel.winfo_exists():
            self._build()

        if self._toplevel is None or self._combo is None or self._combo_var is None:
            logger.warning("FloatingPlacementDialog: build failed — skipping show")
            return

        # populate suggestions
        self._combo.config(values=suggestions)
        if suggestions:
            self._combo_var.set(suggestions[0])
            self._combo.select_range(0, tk.END)

        self._position()
        self._toplevel.deiconify()
        self._toplevel.lift()
        self._toplevel.attributes("-topmost", True)
        self._combo.focus_set()

        logger.debug(
            "FloatingPlacementDialog: shown (%d suggestions)", len(suggestions)
        )

    def hide(self) -> None:
        """Hide the dialog immediately."""
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.withdraw()

    def destroy(self) -> None:
        """Destroy on app close."""
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.destroy()
        self._toplevel = None
        self._combo = None
        self._combo_var = None

    def is_visible(self) -> bool:
        """Return True if the dialog is currently shown."""
        if self._toplevel is None or not self._toplevel.winfo_exists():
            return False
        return self._toplevel.state() == "normal"

    # ── internal ──────────────────────────────────────────────────────

    def _build(self) -> None:
        """Create the Toplevel and all widgets."""
        t = self._theme
        top = tk.Toplevel(self._parent)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.attributes("-alpha", _WIN_ALPHA)
        top.configure(bg=t.bg_primary)
        top.withdraw()  # start hidden; show() calls deiconify()

        # ── outer border frame ─────────────────────────────────────
        border_frame = tk.Frame(top, bg=t.fg_accent, padx=1, pady=1)
        border_frame.pack(fill=tk.BOTH, expand=True)

        inner_frame = tk.Frame(border_frame, bg=t.bg_primary)
        inner_frame.pack(fill=tk.BOTH, expand=True)

        # ── header bar ────────────────────────────────────────────
        header = tk.Frame(inner_frame, bg=t.bg_header, height=24)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(
            header, text="📍 Placement Query",
            bg=t.bg_header, fg=t.fg_dim,
            font=t.font("small", bold=True),
        ).pack(side=tk.LEFT, padx=6)

        close_btn = tk.Label(
            header, text="✕",
            bg=t.bg_header, fg=t.fg_error,
            font=t.font("small"), cursor="hand2",
        )
        close_btn.pack(side=tk.RIGHT, padx=6)
        close_btn.bind("<Button-1>", lambda _e: self.hide())

        # ── input row ─────────────────────────────────────────────
        input_frame = tk.Frame(inner_frame, bg=t.bg_primary)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 4))

        combo_var = tk.StringVar()
        combo = ttk.Combobox(
            input_frame,
            textvariable=combo_var,
            font=t.font("normal"),
            state="normal",
        )
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        combo.bind("<Return>", lambda _e: self._submit())
        combo.bind("<Escape>", lambda _e: self.hide())

        ask_btn = tk.Button(
            input_frame, text="Ask",
            bg=t.bg_header, fg=t.fg_accent,
            font=t.font("small", bold=True),
            bd=0, activebackground=t.bg_button_hover,
            cursor="hand2", padx=10, pady=2,
            command=self._submit,
        )
        ask_btn.pack(side=tk.LEFT)

        # ── footer hint ────────────────────────────────────────────
        footer = tk.Frame(inner_frame, bg=t.bg_footer, height=18)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        tk.Label(
            footer, text="Enter to submit  •  Esc to dismiss",
            bg=t.bg_footer, fg=t.fg_dim, font=t.font("small"),
        ).pack(side=tk.LEFT, padx=6)

        self._toplevel = top
        self._combo = combo
        self._combo_var = combo_var
        logger.debug("FloatingPlacementDialog: built")

    def _submit(self) -> None:
        """Read prompt, hide dialog, invoke on_submit callback."""
        if self._combo_var is None:
            return
        prompt = self._combo_var.get().strip()
        if not prompt:
            return
        # hide before capture so dialog does not appear in the screenshot
        self.hide()
        if self._on_submit is not None:
            self._on_submit(prompt)

    def _position(self) -> None:
        """Position window centered horizontally, vertical center vertically."""
        if self._toplevel is None:
            return

        screen_w = self._parent.winfo_screenwidth()
        screen_h = self._parent.winfo_screenheight()

        win_w = max(_WIN_MIN_WIDTH, int(screen_w * _WIN_WIDTH_FRACTION))
        win_h = max(_WIN_MIN_HEIGHT, int(screen_h * _WIN_HEIGHT_FRACTION))

        win_x = (screen_w - win_w) // 2
        win_y = int(screen_h * _WIN_Y_FRACTION)

        self._toplevel.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
