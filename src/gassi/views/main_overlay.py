"""Main overlay window — compact toolbar, collapsible, slide-off-screen, themed.

States:
  - EXPANDED: toolbar + advice area + footer (full overlay)
  - COLLAPSED: toolbar-only strip
  - OFFSCREEN: slid off left edge, only a small tab visible to pull back
"""

import logging
import platform
import tkinter as tk

from gassi.core.overlay.overlay_canvas import OverlayCanvas
from gassi.core.theme.theme import Theme, DARK_THEME

logger = logging.getLogger(__name__)

_TAB_WIDTH = 20
_TAB_HEIGHT = 60


class MainOverlay(tk.Tk):
    """Root overlay window — hosts toolbar, canvas, and footer."""

    def __init__(self, theme: Theme | None = None) -> None:
        super().__init__()

        self._theme = theme or DARK_THEME
        self._click_through_active = False
        self._collapsed = False
        self._offscreen = False
        self._system = platform.system()
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._expanded_geometry: str = ""
        self._onscreen_x: int = 100
        self._onscreen_y: int = 100

        t = self._theme

        self.title("GASSI")
        self.geometry(f"{t.window_width}x{t.window_height}+100+100")
        self.attributes("-topmost", True)
        self.attributes("-alpha", t.window_alpha)
        self.configure(bg=t.bg_primary)
        self.minsize(t.window_min_width, t.window_min_height)
        self.overrideredirect(True)

        # ── toolbar ───────────────────────────────────────────────
        self._toolbar = tk.Frame(
            self, bg=t.bg_header, height=t.header_height, cursor="fleur",
        )
        self._toolbar.pack(fill=tk.X, side=tk.TOP)
        self._toolbar.pack_propagate(False)

        btn_opts: dict = dict(
            bg=t.bg_header, fg=t.fg_button, font=t.font("small"),
            bd=0, activebackground=t.bg_button_hover,
            activeforeground=t.fg_button_active, cursor="hand2",
            padx=3, pady=0,
        )

        # LEFT group: slide-off + collapse (window visibility controls)
        self._slide_btn = tk.Button(
            self._toolbar, text="◀", command=self.toggle_offscreen, **btn_opts,
        )
        self._slide_btn.pack(side=tk.LEFT, padx=(4, 1))

        self._collapse_btn = tk.Button(
            self._toolbar, text="▼", command=self.toggle_collapse, **btn_opts,
        )
        self._collapse_btn.pack(side=tk.LEFT, padx=1)

        # title (small, dim)
        self._title_label = tk.Label(
            self._toolbar, text="GASSI", bg=t.bg_header,
            fg=t.fg_dim, font=t.font("small"),
        )
        self._title_label.pack(side=tk.LEFT, padx=(4, 0))

        # status (next to title)
        self._status_label = tk.Label(
            self._toolbar, text="IDLE", bg=t.bg_header,
            fg=t.fg_dim, font=t.font("small"),
        )
        self._status_label.pack(side=tk.LEFT, padx=(4, 0))

        # RIGHT group: lock + close
        self._close_btn = tk.Button(
            self._toolbar, text="✕", command=self._on_close_click,
            bg=t.bg_header, fg=t.fg_error, font=t.font("small"),
            bd=0, activebackground="#cc0000", activeforeground="#ffffff",
            cursor="hand2", padx=3, pady=0,
        )
        self._close_btn.pack(side=tk.RIGHT, padx=(1, 4))

        self._lock_btn = tk.Button(
            self._toolbar, text="🔓", command=self.toggle_click_through, **btn_opts,
        )
        self._lock_btn.pack(side=tk.RIGHT, padx=1)

        # draggable toolbar
        for widget in (self._toolbar, self._title_label, self._status_label):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

        # ── body (collapsible) ────────────────────────────────────
        self._body = tk.Frame(self, bg=t.bg_primary)
        self._body.pack(fill=tk.BOTH, expand=True)

        self.canvas = OverlayCanvas(self._body, theme=t)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # footer
        self._footer = tk.Frame(self._body, bg=t.bg_footer, height=t.footer_height)
        self._footer.pack(fill=tk.X, side=tk.BOTTOM)
        self._footer.pack_propagate(False)

        self._hints_label = tk.Label(
            self._footer,
            text="F1 Advisor  │  F2 Placement  │  F3 Lock",
            bg=t.bg_footer, fg=t.fg_button, font=t.font("small"),
        )
        self._hints_label.pack(side=tk.LEFT, padx=t.padding_x)

        self._cooldown_label = tk.Label(
            self._footer, text="", bg=t.bg_footer,
            fg=t.fg_warning, font=t.font("small", bold=True),
        )
        self._cooldown_label.pack(side=tk.RIGHT, padx=t.padding_x)

        # ── pull-back tab (visible when offscreen) ────────────────
        # This is a tiny bar that sticks out from the left screen edge
        self._tab_window: tk.Toplevel | None = None

    # ── status ────────────────────────────────────────────────────────

    def update_status(self, mode: str, source: str = "") -> None:
        t = self._theme
        text = mode.upper()
        if source:
            text += f" [{source}]"
        is_active = mode.lower() not in ("idle", "")
        self._status_label.config(
            text=text, fg=t.fg_accent if is_active else t.fg_dim,
        )

    def update_cooldown(self, text: str) -> None:
        self._cooldown_label.config(text=text)

    # ── collapse / expand ─────────────────────────────────────────────

    def toggle_collapse(self) -> None:
        if self._collapsed:
            self.expand()
        else:
            self.collapse()

    def collapse(self) -> None:
        if self._collapsed:
            return
        self._collapsed = True
        self._expanded_geometry = self.geometry()
        self._body.pack_forget()

        t = self._theme
        w = self.winfo_width()
        self.geometry(f"{w}x{t.toolbar_collapsed_height}")
        self.minsize(t.window_min_width, t.toolbar_collapsed_height)
        self.attributes("-alpha", t.window_alpha_collapsed)
        self._collapse_btn.config(text="▲")

    def expand(self) -> None:
        if not self._collapsed:
            return
        self._collapsed = False
        self._body.pack(fill=tk.BOTH, expand=True)

        t = self._theme
        if self._expanded_geometry:
            self.geometry(self._expanded_geometry)
        self.minsize(t.window_min_width, t.window_min_height)
        self.attributes("-alpha", t.window_alpha)
        self._collapse_btn.config(text="▼")

    def auto_expand_for_result(self) -> None:
        if self._offscreen:
            self.slide_onscreen()
        if self._collapsed:
            self.expand()

    # ── slide offscreen / onscreen ────────────────────────────────────

    def toggle_offscreen(self) -> None:
        if self._offscreen:
            self.slide_onscreen()
        else:
            self.slide_offscreen()

    def slide_offscreen(self) -> None:
        """Slide the overlay off the left edge of the screen."""
        if self._offscreen:
            return
        self._offscreen = True
        self._onscreen_x = self.winfo_x()
        self._onscreen_y = self.winfo_y()

        # move window fully off left edge
        w = self.winfo_width()
        self.geometry(f"+{-w}+{self._onscreen_y}")

        # create the pull-back tab
        self._create_pull_tab()
        self._slide_btn.config(text="▶")
        logger.info("Overlay slid offscreen")

    def slide_onscreen(self) -> None:
        """Bring the overlay back to its previous position."""
        if not self._offscreen:
            return
        self._offscreen = False
        self.geometry(f"+{self._onscreen_x}+{self._onscreen_y}")
        self._destroy_pull_tab()
        self._slide_btn.config(text="◀")
        logger.info("Overlay slid onscreen")

    def _create_pull_tab(self) -> None:
        """Create a small tab at the left screen edge to pull the overlay back."""
        self._destroy_pull_tab()
        t = self._theme

        tab = tk.Toplevel(self)
        tab.overrideredirect(True)
        tab.attributes("-topmost", True)
        tab.attributes("-alpha", 0.7)
        tab.geometry(f"{_TAB_WIDTH}x{_TAB_HEIGHT}+0+{self._onscreen_y}")
        tab.configure(bg=t.bg_header)

        tab_btn = tk.Label(
            tab, text="▶", bg=t.bg_header, fg=t.fg_accent,
            font=t.font("small", bold=True), cursor="hand2",
        )
        tab_btn.pack(fill=tk.BOTH, expand=True)
        tab_btn.bind("<Button-1>", lambda _e: self.slide_onscreen())

        self._tab_window = tab

    def _destroy_pull_tab(self) -> None:
        if self._tab_window is not None:
            self._tab_window.destroy()
            self._tab_window = None

    # ── click-through toggle ──────────────────────────────────────────

    def toggle_click_through(self) -> None:
        if self._click_through_active:
            self._disable_click_through()
        else:
            self._enable_click_through()

    def _enable_click_through(self) -> None:
        self._click_through_active = True
        self._lock_btn.config(text="🔒")
        t = self._theme
        self.attributes("-alpha", t.window_alpha_locked)

        if self._system == "Windows":
            self._set_windows_click_through(True)
        elif self._system == "Darwin":
            self._set_macos_click_through(True)
        logger.info("Click-through enabled")

    def _disable_click_through(self) -> None:
        self._click_through_active = False
        self._lock_btn.config(text="🔓")
        t = self._theme
        alpha = t.window_alpha_collapsed if self._collapsed else t.window_alpha
        self.attributes("-alpha", alpha)

        if self._system == "Windows":
            self._set_windows_click_through(False)
        elif self._system == "Darwin":
            self._set_macos_click_through(False)
        logger.info("Click-through disabled")

    def _set_windows_click_through(self, enabled: bool) -> None:
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

    # ── close ─────────────────────────────────────────────────────────

    def set_close_handler(self, handler: object) -> None:
        self._close_handler = handler

    def _on_close_click(self) -> None:
        self._destroy_pull_tab()
        if hasattr(self, "_close_handler") and self._close_handler:
            self._close_handler()  # type: ignore[operator]
        else:
            self.destroy()
