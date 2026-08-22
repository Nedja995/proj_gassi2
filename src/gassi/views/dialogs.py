"""Simple input dialogs for user prompts."""

import tkinter as tk
from tkinter import ttk
from typing import Callable


class PlacementPromptDialog(tk.Toplevel):
    """Modal dialog for entering a placement question.

    Appears centered over the parent overlay when F2 is pressed.
    Submits the user's question to the provided callback on Enter or button click.
    """

    _DEFAULT_WIDTH = 450
    _DEFAULT_HEIGHT = 130

    def __init__(self, parent: tk.Tk, on_submit: Callable[[str], None]) -> None:
        super().__init__(parent)
        self._on_submit = on_submit
        self._result: str | None = None

        self.title("GASSI — Placement Query")
        self.geometry(f"{self._DEFAULT_WIDTH}x{self._DEFAULT_HEIGHT}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._center_on_parent(parent)
        self._entry.focus_set()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="What do you need help placing?",
            font=("Consolas", 10),
        ).pack(anchor="w")

        self._entry = ttk.Entry(frame, font=("Consolas", 10))
        self._entry.pack(fill=tk.X, pady=(8, 10))
        self._entry.insert(0, "Where should I build next?")
        self._entry.select_range(0, tk.END)
        self._entry.bind("<Return>", lambda _e: self._submit())
        self.bind("<Escape>", lambda _e: self.destroy())

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Ask", command=self._submit).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

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
