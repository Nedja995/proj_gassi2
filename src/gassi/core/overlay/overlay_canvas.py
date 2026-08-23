"""Layered overlay surface with scrollable advice text.

v1 uses the scrollable Text widget for advice display.
v2 layers (highlights, arrows, overlays) are scaffolded on an
internal Canvas for future tutorial/placement rendering.
"""

import re
import tkinter as tk
from tkinter import ttk

from gassi.core.theme.theme import Theme

# inline bold pattern — matches **text**
_RE_BOLD = re.compile(r"(\*\*.*?\*\*)")

# line-level markdown patterns (checked in order, first match wins)
_RE_H2 = re.compile(r"^##\s+(.+)")
_RE_H3 = re.compile(r"^###\s+(.+)")
_RE_BULLET = re.compile(r"^[-*]\s+(.+)")


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
            spacing3=3,
        )

        scrollbar = ttk.Scrollbar(self, command=self._text_area.yview)
        self._text_area.configure(yscrollcommand=scrollbar.set)

        self._text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ── text tags ─────────────────────────────────────────────
        t = theme
        self._text_area.tag_configure(
            "advice", foreground=t.fg_accent,
        )
        self._text_area.tag_configure(
            "bold", foreground=t.fg_accent, font=t.font("normal", bold=True),
        )
        self._text_area.tag_configure(
            "h2",
            foreground=t.fg_accent,
            font=t.font("normal", bold=True),
            spacing1=6,    # px above the heading line
            spacing3=2,    # px below
        )
        self._text_area.tag_configure(
            "h3",
            foreground=t.fg_text if hasattr(t, "fg_text") else t.fg_dim,
            font=t.font("normal", bold=True),
            spacing1=4,
            spacing3=1,
        )
        self._text_area.tag_configure(
            "bullet",
            foreground=t.fg_accent,
            lmargin1=t.padding_x + 2,   # hanging indent — first line
            lmargin2=t.padding_x + 14,  # continuation lines line up after bullet
            spacing1=1,
            spacing3=1,
        )
        self._text_area.tag_configure(
            "bullet_bold",
            foreground=t.fg_accent,
            font=t.font("normal", bold=True),
            lmargin1=t.padding_x + 2,
            lmargin2=t.padding_x + 14,
            spacing1=1,
            spacing3=1,
        )
        self._text_area.tag_configure(
            "loading", foreground=t.fg_loading,
        )
        self._text_area.tag_configure(
            "error", foreground=t.fg_error,
        )
        self._text_area.tag_configure(
            "dim", foreground=t.fg_dim,
        )

    # ── v1: text display ──────────────────────────────────────────────

    def show_advice(self, text: str, is_loading: bool = False) -> None:
        """Display advice text with markdown rendering.

        Supported markdown:
            ## Heading       → bold accent heading
            ### Heading      → bold dim subheading
            - item / * item  → • bullet with indent
            **bold**         → inline bold (inside any line type)
        """
        self._text_area.config(state=tk.NORMAL)
        self._text_area.delete("1.0", tk.END)

        if is_loading:
            self._text_area.insert("1.0", text, "loading")
        else:
            self._render_markdown(text)

        self._text_area.config(state=tk.DISABLED)
        self._text_area.see("1.0")

    def _render_markdown(self, text: str) -> None:
        """Parse and render markdown line-by-line into the Text widget."""
        lines = text.splitlines()
        first_line = True

        for raw_line in lines:
            line = raw_line.rstrip()

            # blank line — just a newline spacer
            if not line:
                if not first_line:
                    self._text_area.insert(tk.END, "\n")
                continue

            if not first_line:
                self._text_area.insert(tk.END, "\n")
            first_line = False

            # ## heading
            m = _RE_H2.match(line)
            if m:
                self._insert_inline(m.group(1), base_tag="h2")
                continue

            # ### heading
            m = _RE_H3.match(line)
            if m:
                self._insert_inline(m.group(1), base_tag="h3")
                continue

            # - / * bullet
            m = _RE_BULLET.match(line)
            if m:
                self._text_area.insert(tk.END, "• ", "bullet")
                self._insert_inline(m.group(1), base_tag="bullet")
                continue

            # plain paragraph line
            self._insert_inline(line, base_tag="advice")

    def _insert_inline(self, text: str, base_tag: str) -> None:
        """Insert a text fragment, rendering **bold** spans inline.

        base_tag controls the non-bold style; bold spans use a derived tag
        that preserves the base tag's indent/spacing while adding bold font.
        """
        bold_tag = "bold" if base_tag in ("advice", "h2", "h3") else "bullet_bold"

        parts = _RE_BOLD.split(text)
        for part in parts:
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                self._text_area.insert(tk.END, part[2:-2], bold_tag)
            else:
                self._text_area.insert(tk.END, part, base_tag)

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
