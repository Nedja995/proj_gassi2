"""Inline placement input strip — replaces the popup PlacementPromptDialog.

A collapsible bar that slides up from the overlay footer. Contains a
Combobox (shows history + quick-prompts as dropdown) with a Submit button.
Toggled by F2 hotkey. Dismissed on submit or Escape.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from gassi.core.theme.theme import Theme


class PlacementInputStrip(tk.Frame):
    """Inline input strip packed inside the overlay body above the footer."""

    def __init__(
        self,
        parent: tk.Widget,
        theme: Theme,
        on_submit: Callable[[str], None],
        canvas_ref: tk.Widget | None = None,
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("bg", theme.bg_footer)
        super().__init__(parent, **kwargs)
        self._theme = theme
        self._on_submit = on_submit
        self._canvas_ref = canvas_ref
        self._visible = False
        t = theme

        # header label
        tk.Label(
            self, text="📍 Placement",
            bg=t.bg_footer, fg=t.fg_dim,
            font=t.font("small", bold=True),
        ).pack(side=tk.LEFT, padx=(6, 4))

        # combobox — editable so user can type freely
        self._combo_var = tk.StringVar()
        self._combo = ttk.Combobox(
            self,
            textvariable=self._combo_var,
            font=t.font("small"),
            values=[],
            state="normal",
            width=38,
        )
        self._combo.pack(side=tk.LEFT, padx=(0, 4), pady=3)
        self._combo.bind("<Return>", lambda _e: self._submit())
        self._combo.bind("<Escape>", lambda _e: self.hide())

        # submit button
        tk.Button(
            self, text="Ask",
            bg=t.bg_header, fg=t.fg_accent,
            font=t.font("small", bold=True),
            bd=0, activebackground=t.bg_button_hover,
            cursor="hand2", padx=8, pady=1,
            command=self._submit,
        ).pack(side=tk.LEFT, padx=(0, 4))

        # dismiss button
        tk.Button(
            self, text="✕",
            bg=t.bg_footer, fg=t.fg_dim,
            font=t.font("small"),
            bd=0, activebackground=t.bg_button_hover,
            cursor="hand2", padx=4, pady=1,
            command=self.hide,
        ).pack(side=tk.LEFT)

    # ── public API ────────────────────────────────────────────────────

    def show(self, suggestions: list[str]) -> None:
        """Show the strip with updated suggestions and focus the input."""
        if not self._visible:
            self._visible = True
            if self._canvas_ref is not None:
                self._canvas_ref.pack_forget()
            self.pack(fill=tk.X, side=tk.BOTTOM)
            if self._canvas_ref is not None:
                self._canvas_ref.pack(fill=tk.BOTH, expand=True)

        self._combo.config(values=suggestions)
        if not self._combo_var.get().strip() and suggestions:
            self._combo_var.set(suggestions[0])
        self._combo.select_range(0, tk.END)
        self._combo.focus_set()

    def hide(self) -> None:
        """Hide the strip."""
        if self._visible:
            self._visible = False
            self.pack_forget()

    def toggle(self, suggestions: list[str]) -> None:
        if self._visible:
            self.hide()
        else:
            self.show(suggestions)

    @property
    def is_visible(self) -> bool:
        return self._visible

    # ── internals ─────────────────────────────────────────────────────

    def _submit(self) -> None:
        prompt = self._combo_var.get().strip()
        if not prompt:
            return
        self.hide()
        self._on_submit(prompt)
