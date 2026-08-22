"""Settings dialog — configurable hotkeys, theme, cooldown, model.

Accessible via gear icon in the toolbar. All changes are saved
to a persistent JSON config and applied immediately where possible.
Hotkey changes require an app restart to take effect (pynput limitation).
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from gassi.core.theme.theme import Theme, THEMES, DARK_THEME
from gassi.core.settings_manager import load_saved_settings, save_settings


# pynput key display names for common keys
_KEY_DISPLAY = {
    "<f1>": "F1", "<f2>": "F2", "<f3>": "F3", "<f4>": "F4",
    "<f5>": "F5", "<f6>": "F6", "<f7>": "F7", "<f8>": "F8",
    "<f9>": "F9", "<f10>": "F10", "<f11>": "F11", "<f12>": "F12",
    "<shift>": "Shift", "<ctrl>": "Ctrl", "<alt>": "Alt",
}


def _display_hotkey(hotkey_str: str) -> str:
    """Convert pynput hotkey string to readable display."""
    parts = hotkey_str.split("+")
    display_parts = []
    for part in parts:
        part = part.strip()
        display_parts.append(_KEY_DISPLAY.get(part, part.strip("<>")))
    return " + ".join(display_parts)


class HotkeyCapture(tk.Frame):
    """Widget that captures a key press and stores the pynput string."""

    def __init__(
        self, parent: tk.Widget, theme: Theme, initial_value: str, **kwargs: Any
    ) -> None:
        super().__init__(parent, bg=theme.bg_primary, **kwargs)
        self._theme = theme
        self._value = initial_value
        self._capturing = False

        self._display_label = tk.Label(
            self,
            text=_display_hotkey(initial_value),
            bg=theme.bg_input,
            fg=theme.fg_text,
            font=theme.font("normal"),
            width=16,
            anchor="center",
            relief=tk.FLAT,
            padx=4,
            pady=2,
        )
        self._display_label.pack(side=tk.LEFT)

        self._capture_btn = tk.Button(
            self,
            text="Set",
            bg=theme.bg_header,
            fg=theme.fg_button,
            font=theme.font("small"),
            bd=0,
            activebackground=theme.bg_button_hover,
            cursor="hand2",
            command=self._start_capture,
            padx=6,
        )
        self._capture_btn.pack(side=tk.LEFT, padx=(4, 0))

    @property
    def value(self) -> str:
        return self._value

    def _start_capture(self) -> None:
        self._capturing = True
        t = self._theme
        self._display_label.config(text="Press a key...", fg=t.fg_warning)
        self._capture_btn.config(text="...", state=tk.DISABLED)
        # bind to the toplevel to catch key events
        top = self.winfo_toplevel()
        top.bind("<Key>", self._on_key_press)

    def _on_key_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._capturing:
            return
        self._capturing = False
        top = self.winfo_toplevel()
        top.unbind("<Key>")

        # build pynput-compatible string
        key_name = event.keysym.lower()
        modifiers: list[str] = []

        if event.state & 0x1:  # Shift
            modifiers.append("<shift>")
        if event.state & 0x4:  # Ctrl
            modifiers.append("<ctrl>")
        if event.state & 0x8:  # Alt
            modifiers.append("<alt>")

        # map tkinter keysym to pynput format
        pynput_key = f"<{key_name}>"

        if modifiers:
            self._value = "+".join(modifiers) + "+" + pynput_key
        else:
            self._value = pynput_key

        t = self._theme
        self._display_label.config(text=_display_hotkey(self._value), fg=t.fg_text)
        self._capture_btn.config(text="Set", state=tk.NORMAL)


class SettingsDialog(tk.Toplevel):
    """Modal settings dialog with tabs for different setting categories."""

    _WIDTH = 480
    _HEIGHT = 420

    def __init__(
        self,
        parent: tk.Tk,
        theme: Theme,
        current_settings: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._on_save = on_save
        self._current = current_settings
        t = theme

        self.title("GASSI — Settings")
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(bg=t.bg_primary)
        self.transient(parent)
        self.grab_set()

        # notebook (tabs)
        style = ttk.Style()
        style.configure("Settings.TNotebook", background=t.bg_primary)
        style.configure(
            "Settings.TNotebook.Tab",
            background=t.bg_header,
            foreground=t.fg_text,
            padding=[10, 4],
        )
        style.map(
            "Settings.TNotebook.Tab",
            background=[("selected", t.bg_primary)],
            foreground=[("selected", t.fg_accent)],
        )

        notebook = ttk.Notebook(self, style="Settings.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        # tabs
        self._hotkeys_frame = self._build_hotkeys_tab(notebook, t)
        self._general_frame = self._build_general_tab(notebook, t)

        notebook.add(self._hotkeys_frame, text="  Hotkeys  ")
        notebook.add(self._general_frame, text="  General  ")

        # bottom buttons
        btn_frame = tk.Frame(self, bg=t.bg_primary)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(
            btn_frame,
            text="Hotkey changes require restart",
            bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_frame, text="Save & Close", command=self._save,
            bg=t.bg_header, fg=t.fg_accent, font=t.font("normal", bold=True),
            bd=0, activebackground=t.bg_button_hover, cursor="hand2",
            padx=12, pady=4,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            btn_frame, text="Cancel", command=self.destroy,
            bg=t.bg_header, fg=t.fg_button, font=t.font("normal"),
            bd=0, activebackground=t.bg_button_hover, cursor="hand2",
            padx=8, pady=4,
        ).pack(side=tk.RIGHT)

        self._center_on_parent(parent)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _build_hotkeys_tab(self, parent: tk.Widget, t: Theme) -> tk.Frame:
        frame = tk.Frame(parent, bg=t.bg_primary, padx=16, pady=16)

        hotkey_defs = [
            ("Advisor (query)", "hotkey_advisor_toggle"),
            ("Switch source", "hotkey_advisor_source_switch"),
            ("Placement", "hotkey_placement"),
            ("Lock overlay", "hotkey_lock_overlay"),
        ]

        tk.Label(
            frame, text="Rebind hotkeys to avoid conflicts with your game.",
            bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self._hotkey_captures: dict[str, HotkeyCapture] = {}

        for i, (label, key) in enumerate(hotkey_defs, start=1):
            tk.Label(
                frame, text=label, bg=t.bg_primary, fg=t.fg_text,
                font=t.font("normal"), anchor="w",
            ).grid(row=i, column=0, sticky="w", pady=6, padx=(0, 16))

            current_val = self._current.get(key, "")
            capture = HotkeyCapture(frame, t, current_val)
            capture.grid(row=i, column=1, sticky="w", pady=6)
            self._hotkey_captures[key] = capture

        frame.columnconfigure(1, weight=1)
        return frame

    def _build_general_tab(self, parent: tk.Widget, t: Theme) -> tk.Frame:
        frame = tk.Frame(parent, bg=t.bg_primary, padx=16, pady=16)
        row = 0

        # theme picker
        tk.Label(
            frame, text="Theme", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._theme_var = tk.StringVar(value=self._current.get("theme_name", "dark"))
        theme_menu = ttk.Combobox(
            frame, textvariable=self._theme_var,
            values=list(THEMES.keys()), state="readonly", width=18,
        )
        theme_menu.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # cooldown
        tk.Label(
            frame, text="Cooldown (seconds)", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._cooldown_var = tk.DoubleVar(
            value=self._current.get("cooldown_seconds", 15.0)
        )
        cooldown_frame = tk.Frame(frame, bg=t.bg_primary)
        cooldown_frame.grid(row=row, column=1, sticky="w", pady=6)

        self._cooldown_scale = tk.Scale(
            cooldown_frame, from_=5, to=60, orient=tk.HORIZONTAL,
            variable=self._cooldown_var, length=140,
            bg=t.bg_primary, fg=t.fg_text, highlightthickness=0,
            troughcolor=t.bg_input, activebackground=t.fg_accent,
            font=t.font("small"),
        )
        self._cooldown_scale.pack(side=tk.LEFT)
        row += 1

        # AI model
        tk.Label(
            frame, text="AI Model", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._model_var = tk.StringVar(
            value=self._current.get("gemini_model", "gemini-3.6-flash")
        )
        model_entry = tk.Entry(
            frame, textvariable=self._model_var,
            bg=t.bg_input, fg=t.fg_text, font=t.font("normal"),
            insertbackground=t.fg_accent, bd=1, relief=tk.FLAT, width=22,
        )
        model_entry.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # advisor input source
        tk.Label(
            frame, text="Default input", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._source_var = tk.StringVar(
            value=self._current.get("advisor_input_source", "ocr")
        )
        source_menu = ttk.Combobox(
            frame, textvariable=self._source_var,
            values=["ocr", "screenshot"], state="readonly", width=18,
        )
        source_menu.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        frame.columnconfigure(1, weight=1)
        return frame

    def _save(self) -> None:
        """Collect all settings and save."""
        settings: dict[str, Any] = {}

        # hotkeys
        for key, capture in self._hotkey_captures.items():
            settings[key] = capture.value

        # general
        settings["theme_name"] = self._theme_var.get()
        settings["cooldown_seconds"] = self._cooldown_var.get()
        settings["gemini_model"] = self._model_var.get()
        settings["advisor_input_source"] = self._source_var.get()

        save_settings(settings)
        self._on_save(settings)
        self.destroy()

    def _center_on_parent(self, parent: tk.Tk) -> None:
        parent.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - self._WIDTH) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self._HEIGHT) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")
