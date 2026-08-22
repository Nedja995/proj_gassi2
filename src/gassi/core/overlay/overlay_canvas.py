"""Layered drawing canvas for advice text, highlights, arrows, and tutorials.

v1 uses only the 'text' layer. Higher layers (highlights, arrows, overlays)
are scaffolded now so v2 tutorial/placement rendering is additive, not a rewrite.
"""

import tkinter as tk


class OverlayCanvas(tk.Canvas):
    """Multi-layer transparent canvas for drawing over the game window."""

    _LAYER_NAMES = ("text", "highlights", "arrows", "overlays")

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(parent, bg="black", highlightthickness=0, **kwargs)
        self._layers: dict[str, list[int]] = {name: [] for name in self._LAYER_NAMES}

    # ── layer management ──────────────────────────────────────────────

    def clear_layer(self, layer: str) -> None:
        """Remove all canvas items belonging to a specific layer."""
        for item_id in self._layers[layer]:
            self.delete(item_id)
        self._layers[layer].clear()

    def clear_all_layers(self) -> None:
        """Remove all drawn items from every layer."""
        for layer in self._LAYER_NAMES:
            self.clear_layer(layer)

    # ── v1: text layer ────────────────────────────────────────────────

    def draw_text_advice(self, text: str, x: int, y: int) -> None:
        """Display advice text on the overlay."""
        self.clear_layer("text")
        item_id = self.create_text(
            x, y,
            text=text,
            fill="#00FF88",
            font=("Consolas", 11),
            anchor="nw",
            width=self.winfo_width() - x - 20,
        )
        self._layers["text"].append(item_id)

    def draw_status_bar(self, mode_label: str, source_label: str) -> None:
        """Draw a small status indicator at the top of the overlay."""
        self.clear_layer("text")
        status_text = f"[{mode_label}] source: {source_label}"
        item_id = self.create_text(
            10, 5,
            text=status_text,
            fill="#AAAAAA",
            font=("Consolas", 9),
            anchor="nw",
        )
        self._layers["text"].append(item_id)

    # ── v2: highlight layer (scaffolded) ──────────────────────────────

    def draw_highlight_region(
        self, x: int, y: int, w: int, h: int, label: str = ""
    ) -> None:
        """Highlight a rectangular region with a dashed border."""
        item_id = self.create_rectangle(
            x, y, x + w, y + h,
            outline="yellow", width=2, fill="", dash=(4, 4),
        )
        self._layers["highlights"].append(item_id)
        if label:
            text_id = self.create_text(
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
        item_id = self.create_line(
            from_x, from_y, to_x, to_y,
            arrow="last", arrowshape=(20, 20, 10), fill="cyan", width=3,
        )
        self._layers["arrows"].append(item_id)
        if label:
            mid_x = (from_x + to_x) // 2
            mid_y = (from_y + to_y) // 2
            text_id = self.create_text(
                mid_x, mid_y - 15,
                text=label, fill="cyan", font=("Consolas", 9, "bold"),
            )
            self._layers["arrows"].append(text_id)

    # ── v2: tutorial overlay layer (scaffolded) ───────────────────────

    def draw_tutorial_overlay(
        self, x: int, y: int, w: int, h: int, instruction: str
    ) -> None:
        """Dim background + highlighted region + instruction text."""
        bg_id = self.create_rectangle(
            0, 0, self.winfo_width(), self.winfo_height(),
            fill="black", stipple="gray50",
        )
        self._layers["overlays"].append(bg_id)

        box_id = self.create_rectangle(
            x, y, x + w, y + h, outline="lime", width=3, fill="",
        )
        self._layers["overlays"].append(box_id)

        text_id = self.create_text(
            x + w // 2, y + h + 20,
            text=instruction, fill="lime", font=("Consolas", 11, "bold"),
        )
        self._layers["overlays"].append(text_id)
