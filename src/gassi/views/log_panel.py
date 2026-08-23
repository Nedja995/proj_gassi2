"""Collapsible log viewer panel for the main overlay.

Displays the last N log lines from OverlayLogHandler in a scrollable
Text widget. Auto-refreshes every _POLL_MS milliseconds when visible.

Layout contract: pack() is managed by the caller (MainOverlay).
"""

import tkinter as tk
from tkinter import ttk

from gassi.core.log_handler import OverlayLogHandler
from gassi.core.theme.theme import Theme

_POLL_MS = 500          # refresh interval when panel is visible
_DISPLAY_LINES = 80     # lines fetched per refresh
_PANEL_HEIGHT = 120     # px — fixed height so it doesn't steal overlay space


_LEVEL_COLORS = {
    "D": "#6c757d",   # DEBUG  → dim grey
    "I": "#adb5bd",   # INFO   → light grey
    "W": "#ffc107",   # WARNING → amber
    "E": "#dc3545",   # ERROR  → red
    "C": "#ff0000",   # CRITICAL → bright red
}


class LogPanel(tk.Frame):
    """Scrollable, auto-refreshing log viewer panel."""

    def __init__(
        self,
        parent: tk.Widget,
        theme: Theme,
        log_handler: OverlayLogHandler,
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("bg", theme.bg_primary)
        super().__init__(parent, **kwargs)
        self._theme = theme
        self._log_handler = log_handler
        self._visible = False
        self._after_id: str | None = None
        self._last_line_count = 0

        t = theme

        # header bar with label and clear button
        header = tk.Frame(self, bg=t.bg_footer, height=18)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="LOG",
            bg=t.bg_footer,
            fg=t.fg_dim,
            font=t.font("small", bold=True),
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            header,
            text="CLR",
            bg=t.bg_footer,
            fg=t.fg_dim,
            font=t.font("small"),
            bd=0,
            activebackground=t.bg_button_hover,
            activeforeground=t.fg_button_active,
            cursor="hand2",
            padx=3,
            pady=0,
            command=self._on_clear,
        ).pack(side=tk.RIGHT, padx=4)

        # scrollable text area
        text_frame = tk.Frame(self, bg=t.bg_primary)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self._text = tk.Text(
            text_frame,
            bg=t.bg_primary,
            fg=t.fg_dim,
            font=t.font("small"),
            wrap=tk.NONE,       # horizontal scroll for long lines
            bd=0,
            padx=4,
            pady=2,
            state=tk.DISABLED,
            cursor="arrow",
            height=6,           # approx _PANEL_HEIGHT in rows
        )

        _v_scroll = ttk.Scrollbar(text_frame, command=self._text.yview)
        _h_scroll = ttk.Scrollbar(
            text_frame, orient=tk.HORIZONTAL, command=self._text.xview
        )
        self._text.configure(
            yscrollcommand=_v_scroll.set,
            xscrollcommand=_h_scroll.set,
        )

        _h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        _v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # colour tags — one per level initial letter
        for level_char, colour in _LEVEL_COLORS.items():
            self._text.tag_configure(f"lvl_{level_char}", foreground=colour)

    # ── public API ────────────────────────────────────────────────────

    def show(self) -> None:
        """Make panel visible and start auto-refresh."""
        if self._visible:
            return
        self._visible = True
        self._refresh()

    def hide(self) -> None:
        """Stop auto-refresh (called when panel is hidden)."""
        self._visible = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    # ── internals ─────────────────────────────────────────────────────

    def _refresh(self) -> None:
        """Pull new log lines into the text widget."""
        current_count = self._log_handler.line_count
        if current_count != self._last_line_count:
            self._last_line_count = current_count
            self._render_lines()

        if self._visible:
            self._after_id = self.after(_POLL_MS, self._refresh)

    def _render_lines(self) -> None:
        lines = self._log_handler.get_lines(last_n=_DISPLAY_LINES)

        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)

        for line in lines:
            tag = self._level_tag(line)
            self._text.insert(tk.END, line + "\n", tag)

        self._text.config(state=tk.DISABLED)
        self._text.see(tk.END)

    @staticmethod
    def _level_tag(line: str) -> str:
        """Extract level initial from formatted line like '15:30:01 [I] ...'."""
        try:
            # format: "HH:MM:SS [X] name: msg"
            bracket_start = line.index("[") + 1
            level_char = line[bracket_start]
            if level_char in _LEVEL_COLORS:
                return f"lvl_{level_char}"
        except (ValueError, IndexError):
            pass
        return "lvl_I"

    def _on_clear(self) -> None:
        self._log_handler.clear()
        self._last_line_count = 0
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.config(state=tk.DISABLED)
