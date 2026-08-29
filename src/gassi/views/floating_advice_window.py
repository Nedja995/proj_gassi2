"""Floating advice window — centered Toplevel for advisor results when overlay is offscreen.

Shown when:
  - The main overlay is slid offscreen (`_offscreen = True`)
  - `show_floating_advice_when_hidden` setting is True
  - An F1 advisor result arrives

Design:
  - Centered on the primary monitor, upper third — avoids covering the game HUD
  - Semi-transparent, always-on-top, themed
  - Reuses OverlayCanvas markdown rendering (same text tags as main overlay)
  - Auto-dismisses after `floating_advice_timeout_seconds`
  - Click anywhere on the window to dismiss early
  - Not click-through — user may want to read and interact
  - Preserved between calls (not destroyed — repositioned and reused)
    so HWND and topmost state are stable across rapid F1 presses

Hide/show:
  - Uses withdraw() / deiconify() — not geometry() move-off-screen.
    Unlike PlacementHighlightWindow, this window has no Win32 region tricks
    and no WS_EX_TRANSPARENT. It's a normal semi-transparent Toplevel.
    HWND recreation on withdraw() is acceptable here — no style bits to preserve.

Non-Windows:
  - alpha transparency works correctly on all platforms for this window type.
  - No platform-specific code needed.
"""

import logging
import platform
import tkinter as tk
from tkinter import ttk

from gassi.core.theme.theme import Theme

logger = logging.getLogger(__name__)

# Fraction of monitor width/height for the floating window
_WIN_WIDTH_FRACTION = 0.35     # 35% of screen width
_WIN_HEIGHT_FRACTION = 0.28    # 28% of screen height
_WIN_MIN_WIDTH = 340
_WIN_MIN_HEIGHT = 180
_WIN_ALPHA = 0.92
# vertical position: upper third of screen (avoids HUD at top and centre game area)
_WIN_Y_FRACTION = 0.08


class FloatingAdviceWindow:
    """Semi-transparent centered Toplevel for advisor results when overlay is hidden.

    Lifecycle is managed by MainOverlay — created once at startup, shown/hidden
    on demand. Never destroyed until app close.
    """

    def __init__(self, parent: tk.Tk, theme: Theme) -> None:
        self._parent = parent
        self._theme = theme
        self._toplevel: tk.Toplevel | None = None
        self._text_area: tk.Text | None = None
        self._dismiss_after_id: str | None = None
        self._system = platform.system()

    # ── public API ────────────────────────────────────────────────────

    def show(self, advice_text: str, timeout_ms: int = 12000) -> None:
        """Display advice_text in the floating window for timeout_ms milliseconds."""
        self._cancel_dismiss()

        if self._toplevel is None or not self._toplevel.winfo_exists():
            self._build()

        if self._toplevel is None or self._text_area is None:
            logger.warning("FloatingAdviceWindow: build failed — skipping show")
            return

        self._render_text(advice_text)
        self._position()
        self._toplevel.deiconify()
        self._toplevel.lift()
        self._toplevel.attributes("-topmost", True)

        self._dismiss_after_id = self._toplevel.after(timeout_ms, self.hide)
        logger.debug(
            "FloatingAdviceWindow: shown (timeout=%dms, len=%d)",
            timeout_ms, len(advice_text),
        )

    def hide(self) -> None:
        """Hide the window immediately."""
        self._cancel_dismiss()
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.withdraw()

    def destroy(self) -> None:
        """Destroy on app close."""
        self._cancel_dismiss()
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.destroy()
        self._toplevel = None
        self._text_area = None

    def is_visible(self) -> bool:
        """Return True if the window is currently shown."""
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

        # ── outer frame with border ────────────────────────────────
        border_frame = tk.Frame(top, bg=t.fg_accent, padx=1, pady=1)
        border_frame.pack(fill=tk.BOTH, expand=True)

        inner_frame = tk.Frame(border_frame, bg=t.bg_primary)
        inner_frame.pack(fill=tk.BOTH, expand=True)

        # ── header bar ────────────────────────────────────────────
        header = tk.Frame(inner_frame, bg=t.bg_header, height=24)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(
            header, text="GASSI  Advisor",
            bg=t.bg_header, fg=t.fg_dim,
            font=t.font("small"),
        ).pack(side=tk.LEFT, padx=6)

        close_btn = tk.Label(
            header, text="✕",
            bg=t.bg_header, fg=t.fg_error,
            font=t.font("small"), cursor="hand2",
        )
        close_btn.pack(side=tk.RIGHT, padx=6)
        close_btn.bind("<Button-1>", lambda _e: self.hide())

        # ── scrollable text area ───────────────────────────────────
        text_frame = tk.Frame(inner_frame, bg=t.bg_primary)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 6))

        text_area = tk.Text(
            text_frame,
            bg=t.bg_primary,
            fg=t.fg_accent,
            font=t.font("normal"),
            wrap=tk.WORD,
            bd=0,
            padx=4,
            pady=4,
            insertbackground=t.fg_accent,
            selectbackground=t.bg_button_hover,
            state=tk.DISABLED,
            cursor="arrow",
            spacing1=2,
            spacing3=3,
        )
        scrollbar = ttk.Scrollbar(text_frame, command=text_area.yview)
        text_area.configure(yscrollcommand=scrollbar.set)
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ── text tags (mirrors OverlayCanvas) ─────────────────────
        text_area.tag_configure("advice", foreground=t.fg_accent)
        text_area.tag_configure(
            "bold", foreground=t.fg_accent, font=t.font("normal", bold=True),
        )
        text_area.tag_configure(
            "h2", foreground=t.fg_accent,
            font=t.font("normal", bold=True), spacing1=6, spacing3=2,
        )
        text_area.tag_configure(
            "h3",
            foreground=t.fg_text if hasattr(t, "fg_text") else t.fg_dim,
            font=t.font("normal", bold=True), spacing1=4,
        )
        text_area.tag_configure(
            "bullet", foreground=t.fg_text if hasattr(t, "fg_text") else t.fg_accent,
            lmargin1=8, lmargin2=16,
        )

        # ── footer hint ────────────────────────────────────────────
        footer = tk.Frame(inner_frame, bg=t.bg_footer, height=18)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        tk.Label(
            footer, text="click ✕ or wait to dismiss",
            bg=t.bg_footer, fg=t.fg_dim, font=t.font("small"),
        ).pack(side=tk.LEFT, padx=6)

        # click anywhere to dismiss (belt + braces with ✕ button)
        for widget in (top, border_frame, inner_frame, text_frame, text_area):
            widget.bind("<Button-1>", self._on_click_dismiss)

        self._toplevel = top
        self._text_area = text_area

        # Apply capture affinity if the parent overlay has requested it (v0.8.2).
        _hide = getattr(self._parent, "_hide_from_capture", False)
        if _hide:
            from gassi.core.capture_affinity import apply_capture_affinity_to_widget  # noqa: PLC0415
            apply_capture_affinity_to_widget(top, hide=True)

        logger.debug("FloatingAdviceWindow: built")

    def _on_click_dismiss(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Dismiss when clicking the window background (not text selection)."""
        # only dismiss on left-click on non-text widgets to allow text selection
        if event.widget is self._text_area:
            return
        self.hide()

    def _position(self) -> None:
        """Position window centered horizontally, upper-third vertically."""
        if self._toplevel is None:
            return

        screen_w = self._parent.winfo_screenwidth()
        screen_h = self._parent.winfo_screenheight()

        win_w = max(_WIN_MIN_WIDTH, int(screen_w * _WIN_WIDTH_FRACTION))
        win_h = max(_WIN_MIN_HEIGHT, int(screen_h * _WIN_HEIGHT_FRACTION))

        win_x = (screen_w - win_w) // 2
        win_y = int(screen_h * _WIN_Y_FRACTION)

        self._toplevel.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")

    def _render_text(self, text: str) -> None:
        """Render markdown advice text using same logic as OverlayCanvas."""
        import re  # noqa: PLC0415

        _RE_BOLD = re.compile(r"(\*\*.*?\*\*)")
        _RE_H2 = re.compile(r"^##\s+(.+)")
        _RE_H3 = re.compile(r"^###\s+(.+)")
        _RE_BULLET = re.compile(r"^[-*]\s+(.+)")

        if self._text_area is None:
            return

        ta = self._text_area
        ta.configure(state=tk.NORMAL)
        ta.delete("1.0", tk.END)

        for line in text.splitlines():
            if m := _RE_H2.match(line):
                ta.insert(tk.END, m.group(1) + "\n", "h2")
            elif m := _RE_H3.match(line):
                ta.insert(tk.END, m.group(1) + "\n", "h3")
            elif m := _RE_BULLET.match(line):
                content = "• " + m.group(1)
                self._insert_inline_bold(ta, content + "\n", "bullet", _RE_BOLD)
            else:
                self._insert_inline_bold(ta, line + "\n", "advice", _RE_BOLD)

        ta.configure(state=tk.DISABLED)
        ta.see("1.0")

    @staticmethod
    def _insert_inline_bold(
        ta: tk.Text,
        line: str,
        base_tag: str,
        bold_re: "re.Pattern[str]",
    ) -> None:
        """Insert a line of text, rendering **bold** spans inline."""
        parts = bold_re.split(line)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                ta.insert(tk.END, part[2:-2], "bold")
            else:
                ta.insert(tk.END, part, base_tag)

    def _cancel_dismiss(self) -> None:
        if self._dismiss_after_id is not None:
            try:
                if self._toplevel and self._toplevel.winfo_exists():
                    self._toplevel.after_cancel(self._dismiss_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._dismiss_after_id = None
