"""Layered overlay surface with scrollable advice text.

v1 uses the scrollable Text widget for advice display.
v2 layers (highlights, arrows, overlays) are scaffolded on an
internal Canvas for future tutorial/placement rendering.
"""

import re
import tkinter as tk
from tkinter import ttk

from gassi.core.theme.theme import Theme


class OverlayCanvas(tk.Frame):
    """Multi-layer overlay surface with scrollable advice text."""

    _LAYER_NAMES = ("highlights", "arrows", "overlays")

    def __init__(self, parent: tk.Widget, theme: Theme, **kwargs: object) -> None:
        kwargs.setdefault("bg", theme.bg_primary)
        super().__init__(parent, **kwargs)
        self._theme = theme

        # v2 canvas layers (for arrows, highlights, tutorial overlays)
        self._canvas = tk.Canvas(self, bg=theme.bg_primary, highlightthickness=0)
        self._layers: dict[str, list[int]] = {name: [] for name in self._LAYER_NAMES}

        # scrollable text area for advice (v1 primary output)
        self._text_area = tk.Text(
            self,
            bg=theme.bg_primary,
            fg=theme.fg_accent,
            font=theme.font("normal"),
            wrap=tk.WORD,
            bd=0,
            padx=theme.padding_x + 2,
            pady=theme.padding_y + 2,
            insertbackground=theme.fg_accent,
            selectbackground=theme.bg_button_hover,
            state=tk.DISABLED,
            cursor="arrow",
            spacing1=2,
            spacing3=2,
        )

        scrollbar = ttk.Scrollbar(self, command=self._text_area.yview)
        self._text_area.configure(yscrollcommand=scrollbar.set)

        self._text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # text tags for styling
        self._text_area.tag_configure("advice", foreground=theme.fg_accent)
        self._text_area.tag_configure("bold", foreground=theme.fg_accent, font=theme.font("normal", bold=True))
        self._text_area.tag_configure("loading", foreground=theme.fg_loading)
        self._text_area.tag_configure("error", foreground=theme.fg_error)
        self._text_area.tag_configure("dim", foreground=theme.fg_dim)

    # ── v1: text display ──────────────────────────────────────────────

    def show_advice(self, text: str, is_loading: bool = False) -> None:
        """Display advice text in the scrollable area.

        Parses **bold** markdown markers into proper bold rendering.
        """
        self._text_area.config(state=tk.NORMAL)
        self._text_area.delete("1.0", tk.END)

        if is_loading:
            self._text_area.insert("1.0", text, "loading")
        else:
            self._insert_with_bold(text)

        self._text_area.config(state=tk.DISABLED)
        self._text_area.see("1.0")

    def _insert_with_bold(self, text: str) -> None:
        """Parse **bold** markers and insert with proper tags."""
        parts = re.split(r"(\*\*.*?\*\*)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self._text_area.insert(tk.END, part[2:-2], "bold")
            else:
                self._text_area.insert(tk.END, part, "advice")

    def append_advice(self, text: str, tag: str = "advice") -> None:
        """Append text without clearing existing content."""
        self._text_area.config(state=tk.NORMAL)
        self._text_area.insert(tk.END, "\n\n" + text, tag)
        self._text_area.config(state=tk.DISABLED)
        self._text_area.see(tk.END)

    def update_status(self, mode: str, source: str = "") -> None:
        """Delegate status update to parent overlay."""
        parent = self.winfo_toplevel()
        if hasattr(parent, "update_status"):
            parent.update_status(mode, source)

    def update_cooldown(self, text: str) -> None:
        """Delegate cooldown update to parent overlay."""
        parent = self.winfo_toplevel()
        if hasattr(parent, "update_cooldown"):
            parent.update_cooldown(text)

    # ── layer management (v2) ─────────────────────────────────────────

    def clear_layer(self, layer: str) -> None:
        for item_id in self._layers[layer]:
            self._canvas.delete(item_id)
        self._layers[layer].clear()

    def clear_all_layers(self) -> None:
        for layer in self._LAYER_NAMES:
            self.clear_layer(layer)
        self.show_advice("")

    # ── v2: scaffolded drawing methods ────────────────────────────────

    def draw_highlight_region(
        self, x: int, y: int, w: int, h: int, label: str = ""
    ) -> None:
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

    def draw_arrow(
        self, from_x: int, from_y: int, to_x: int, to_y: int, label: str = "",
    ) -> None:
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
                text=label, fill="cyan", font=self._theme.font("small", bold=True),
            )
            self._layers["arrows"].append(text_id)

    def draw_tutorial_overlay(
        self, x: int, y: int, w: int, h: int, instruction: str
    ) -> None:
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
            text=instruction, fill="lime", font=self._theme.font("normal", bold=True),
        )
        self._layers["overlays"].append(text_id)
