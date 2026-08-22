"""Layered drawing canvas for advice text, highlights, arrows, and tutorials.

v1 uses only the 'text' layer via a scrollable Text widget.
Higher layers (highlights, arrows, overlays) are scaffolded now
so v2 tutorial/placement rendering is additive, not a rewrite.
"""

import tkinter as tk
from tkinter import ttk

_BG_COLOR = "#1a1a2e"
_TEXT_COLOR = "#00ff88"
_DIM_TEXT_COLOR = "#555555"
_LOADING_COLOR = "#ffaa00"


class OverlayCanvas(tk.Frame):
    """Multi-layer overlay surface with scrollable advice text."""

    _LAYER_NAMES = ("highlights", "arrows", "overlays")

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        kwargs.setdefault("bg", _BG_COLOR)
        super().__init__(parent, **kwargs)

        # v2 canvas layers (for arrows, highlights, tutorial overlays)
        self._canvas = tk.Canvas(self, bg=_BG_COLOR, highlightthickness=0)
        self._layers: dict[str, list[int]] = {name: [] for name in self._LAYER_NAMES}

        # scrollable text area for advice (v1 primary output)
        self._text_area = tk.Text(
            self,
            bg=_BG_COLOR,
            fg=_TEXT_COLOR,
            font=("Consolas", 10),
            wrap=tk.WORD,
            bd=0,
            padx=10,
            pady=8,
            insertbackground=_TEXT_COLOR,
            selectbackground="#2a2a4e",
            state=tk.DISABLED,
            cursor="arrow",
        )

        scrollbar = ttk.Scrollbar(self, command=self._text_area.yview)
        self._text_area.configure(yscrollcommand=scrollbar.set)

        # layout: text area fills the space, scrollbar on right
        # canvas is overlaid on top (for v2 arrows/highlights)
        self._text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # configure text tags for styling
        self._text_area.tag_configure("advice", foreground=_TEXT_COLOR)
        self._text_area.tag_configure("loading", foreground=_LOADING_COLOR)
        self._text_area.tag_configure("error", foreground="#ff4444")
        self._text_area.tag_configure("dim", foreground=_DIM_TEXT_COLOR)

    # ── v1: text display ──────────────────────────────────────────────

    def show_advice(self, text: str, is_loading: bool = False) -> None:
        """Display advice text in the scrollable area."""
        tag = "loading" if is_loading else "advice"
        self._text_area.config(state=tk.NORMAL)
        self._text_area.delete("1.0", tk.END)
        self._text_area.insert("1.0", text, tag)
        self._text_area.config(state=tk.DISABLED)
        self._text_area.see("1.0")

    def append_advice(self, text: str, tag: str = "advice") -> None:
        """Append text without clearing existing content."""
        self._text_area.config(state=tk.NORMAL)
        self._text_area.insert(tk.END, "\n\n" + text, tag)
        self._text_area.config(state=tk.DISABLED)
        self._text_area.see(tk.END)

    def update_status(self, mode: str, source: str = "") -> None:
        """Update status — delegates to parent overlay if available."""
        parent = self.winfo_toplevel()
        if hasattr(parent, "update_status"):
            parent.update_status(mode, source)

    # ── layer management (v2) ─────────────────────────────────────────

    def clear_layer(self, layer: str) -> None:
        """Remove all canvas items belonging to a specific layer."""
        for item_id in self._layers[layer]:
            self._canvas.delete(item_id)
        self._layers[layer].clear()

    def clear_all_layers(self) -> None:
        """Remove all drawn items from every layer and clear text."""
        for layer in self._LAYER_NAMES:
            self.clear_layer(layer)
        self.show_advice("")

    # ── v2: highlight layer (scaffolded) ──────────────────────────────

    def draw_highlight_region(
        self, x: int, y: int, w: int, h: int, label: str = ""
    ) -> None:
        """Highlight a rectangular region with a dashed border."""
        item_id = self._canvas.create_rectangle(
            x, y, x + w, y + h,
            outline="yellow", width=2, fill="", dash=(4, 4),
        )
        self._layers["highlights"].append(item_id)
        if label:
            text_id = self._canvas.create_text(
                x + 5, y + 5, text=label, fill="yellow", anchor="nw",
            )
            self._layers["highlights"].append(text_id)

    # ── v2: arrow layer (scaffolded) ──────────────────────────────────

    def draw_arrow(
        self,
        from_x: int, from_y: int,
        to_x: int, to_y: int,
        label: str = "",
    ) -> None:
        """Draw a directional arrow (for placement suggestions / tutorials)."""
        item_id = self._canvas.create_line(
            from_x, from_y, to_x, to_y,
            arrow="last", arrowshape=(20, 20, 10), fill="cyan", width=3,
        )
        self._layers["arrows"].append(item_id)
        if label:
            mid_x = (from_x + to_x) // 2
            mid_y = (from_y + to_y) // 2
            text_id = self._canvas.create_text(
                mid_x, mid_y - 15,
                text=label, fill="cyan", font=("Consolas", 9, "bold"),
            )
            self._layers["arrows"].append(text_id)

    # ── v2: tutorial overlay layer (scaffolded) ───────────────────────

    def draw_tutorial_overlay(
        self, x: int, y: int, w: int, h: int, instruction: str
    ) -> None:
        """Dim background + highlighted region + instruction text."""
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        bg_id = self._canvas.create_rectangle(
            0, 0, cw, ch, fill="black", stipple="gray50",
        )
        self._layers["overlays"].append(bg_id)

        box_id = self._canvas.create_rectangle(
            x, y, x + w, y + h, outline="lime", width=3, fill="",
        )
        self._layers["overlays"].append(box_id)

        text_id = self._canvas.create_text(
            x + w // 2, y + h + 20,
            text=instruction, fill="lime", font=("Consolas", 11, "bold"),
        )
        self._layers["overlays"].append(text_id)

    # ── cooldown display ────────────────────────────────────────────

    def update_cooldown(self, text: str) -> None:
        """Show or clear the cooldown timer text below the advice area."""
        parent = self.winfo_toplevel()
        if hasattr(parent, "update_cooldown"):
            parent.update_cooldown(text)
