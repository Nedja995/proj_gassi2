"""Simple input dialogs for user prompts."""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from gassi.core.theme.theme import Theme, DARK_THEME


class PlacementPromptDialog(tk.Toplevel):
    """Modal dialog for entering a placement question."""

    _DEFAULT_WIDTH = 420
    _DEFAULT_HEIGHT = 110

    def __init__(
        self,
        parent: tk.Tk,
        on_submit: Callable[[str], None],
        theme: Theme | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_submit = on_submit
        t = theme or DARK_THEME

        self.title("GASSI — Placement Query")
        self.geometry(f"{self._DEFAULT_WIDTH}x{self._DEFAULT_HEIGHT}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(bg=t.bg_primary)
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self, bg=t.bg_primary, padx=12, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame, text="What do you need help placing?",
            bg=t.bg_primary, fg=t.fg_text, font=t.font("normal"),
        ).pack(anchor="w")

        self._entry = tk.Entry(
            frame, font=t.font("normal"),
            bg=t.bg_input, fg=t.fg_text,
            insertbackground=t.fg_accent,
            selectbackground=t.bg_button_hover,
            bd=1, relief=tk.FLAT,
        )
        self._entry.pack(fill=tk.X, pady=(6, 8))
        self._entry.insert(0, "Where should I build next?")
        self._entry.select_range(0, tk.END)
        self._entry.bind("<Return>", lambda _e: self._submit())
        self.bind("<Escape>", lambda _e: self.destroy())

        btn_frame = tk.Frame(frame, bg=t.bg_primary)
        btn_frame.pack(fill=tk.X)

        tk.Button(
            btn_frame, text="Ask", command=self._submit,
            bg=t.bg_header, fg=t.fg_accent, font=t.font("small", bold=True),
            bd=0, activebackground=t.bg_button_hover, cursor="hand2",
            padx=12, pady=2,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            btn_frame, text="Cancel", command=self.destroy,
            bg=t.bg_header, fg=t.fg_button, font=t.font("small"),
            bd=0, activebackground=t.bg_button_hover, cursor="hand2",
            padx=8, pady=2,
        ).pack(side=tk.RIGHT)

        self._center_on_parent(parent)
        self._entry.focus_set()

    def _submit(self) -> None:
        prompt = self._entry.get().strip()
        if prompt:
            self._on_submit(prompt)
        self.destroy()

    def _center_on_parent(self, parent: tk.Tk) -> None:
        parent.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - self._DEFAULT_WIDTH) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self._DEFAULT_HEIGHT) // 2
        self.geometry(f"+{px}+{py}")
