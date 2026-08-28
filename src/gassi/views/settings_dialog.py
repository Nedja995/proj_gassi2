"""Settings dialog — configurable hotkeys, theme, cooldown, model.

Accessible via gear icon in the toolbar. All changes are saved
to a persistent JSON config and applied immediately where possible.
Hotkey changes require an app restart to take effect (pynput limitation).
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

import keyring

from gassi.core.calibration_service import CalibrationService
from gassi.core.ai.gemini_backend import fetch_available_models
from gassi.core.ai.claude_backend import fetch_available_claude_models
from gassi.core.ai.factory import is_claude_available
from gassi.core.game_pack_loader import GamePackLoader
from gassi.core.theme.theme import Theme, THEMES, DARK_THEME
from gassi.core.settings_manager import load_saved_settings, save_settings
from gassi.models.enums import AiProvider


# pynput key display names for common keys
_KEY_DISPLAY = {
    "<f1>": "F1", "<f2>": "F2", "<f3>": "F3", "<f4>": "F4",
    "<f5>": "F5", "<f6>": "F6", "<f7>": "F7", "<f8>": "F8",
    "<f9>": "F9", "<f10>": "F10", "<f11>": "F11", "<f12>": "F12",
    "<shift>": "Shift", "<ctrl>": "Ctrl", "<alt>": "Alt",
}


def _display_hotkey(hotkey_str: str) -> str:
    """Convert pynput hotkey string to readable display.

    Examples:
        '<f1>'          -> 'F1'
        '<alt>+8'       -> 'Alt + 8'
        '<ctrl>+<f2>'   -> 'Ctrl + F2'
        '<shift>+a'     -> 'Shift + A'
    """
    parts = hotkey_str.split("+")
    display_parts = []
    for part in parts:
        part = part.strip()
        if part in _KEY_DISPLAY:
            display_parts.append(_KEY_DISPLAY[part])
        elif part.startswith("<") and part.endswith(">"):
            # unknown special key — strip brackets and capitalise
            display_parts.append(part.strip("<>").upper())
        else:
            # plain character — show uppercase
            display_parts.append(part.upper())
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
            width=22,
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

    # special key names that pynput expects wrapped in angle brackets
    # single printable characters (letters, digits, symbols) must NOT be wrapped
    _SPECIAL_KEYS = frozenset({
        "f1", "f2", "f3", "f4", "f5", "f6",
        "f7", "f8", "f9", "f10", "f11", "f12",
        "space", "return", "escape", "tab", "backspace", "delete",
        "home", "end", "prior", "next",  # prior/next = page up/down
        "up", "down", "left", "right",
        "insert", "pause", "print", "scroll_lock", "num_lock", "caps_lock",
    })

    def _on_key_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._capturing:
            return
        self._capturing = False
        top = self.winfo_toplevel()
        top.unbind("<Key>")

        key_name = event.keysym.lower()
        modifiers: list[str] = []

        if event.state & 0x1:   # Shift
            modifiers.append("<shift>")
        if event.state & 0x4:   # Ctrl
            modifiers.append("<ctrl>")
        # Alt: check both 0x8 (X11/Tk standard) and 0x20000 (Windows Mod2)
        if event.state & 0x8 or event.state & 0x20000:
            modifiers.append("<alt>")

        # skip bare modifier keypresses — wait for an actual key
        if key_name in ("shift_l", "shift_r", "control_l", "control_r",
                        "alt_l", "alt_r", "super_l", "super_r"):
            self._capturing = True
            top.bind("<Key>", self._on_key_press)
            return

        # pynput format: special keys get <>, printable chars do not
        # e.g. F1 -> "<f1>", 8 -> "8", a -> "a", space -> "<space>"
        if key_name in self._SPECIAL_KEYS:
            pynput_key = f"<{key_name}>"
        elif len(key_name) == 1:
            # single printable character — use as-is
            pynput_key = key_name
        else:
            # unknown multi-char key — wrap defensively
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
    _HEIGHT = 640  # increased to accommodate API key fields (v0.8.1.1)

    def __init__(
        self,
        parent: tk.Tk,
        theme: Theme,
        current_settings: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
        calibration_service: CalibrationService | None = None,
        game_id: str = "",
        api_key: str = "",
        claude_api_key: str = "",
        pack_loader: GamePackLoader | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._on_save = on_save
        self._current = current_settings
        self._calibration_service = calibration_service
        self._game_id = game_id
        self._api_key = api_key
        self._claude_api_key = claude_api_key
        self._pack_loader = pack_loader
        t = theme

        self.title("GASSI — Settings")
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(bg=t.bg_primary)
        self.transient(parent)
        self.grab_set()

        # notebook (tabs)
        # Use "default" theme as base so foreground overrides are not
        # stomped by the native Windows "vista" theme.
        style = ttk.Style()
        try:
            style.theme_use("default")
        except tk.TclError:
            pass
        style.configure("Settings.TNotebook", background=t.bg_primary, borderwidth=0)
        style.configure(
            "Settings.TNotebook.Tab",
            background=t.bg_header,
            foreground=t.fg_text,
            padding=[12, 5],
            font=t.font("normal"),
            focuscolor=t.bg_primary,
        )
        style.map(
            "Settings.TNotebook.Tab",
            background=[
                ("selected", t.bg_primary),
                ("active", t.bg_button_hover),
            ],
            foreground=[
                ("selected", t.fg_accent),
                ("active", t.fg_text),
                ("!selected", t.fg_dim),
            ],
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

        # -- active game pack selector -----------------------------------
        tk.Label(
            frame, text="Active game", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        current_game = self._current.get("active_game_id", "timberborn")
        if self._pack_loader is not None:
            packs = self._pack_loader.list_available_packs()
            pack_display = [display for _, display in packs]
            pack_ids = [gid for gid, _ in packs]
            try:
                current_display = pack_display[pack_ids.index(current_game)]
            except ValueError:
                current_display = current_game
                pack_display = [current_game] + pack_display
                pack_ids = [current_game] + pack_ids
        else:
            pack_display = [current_game]
            pack_ids = [current_game]
            current_display = current_game

        self._game_display_to_id = dict(zip(pack_display, pack_ids))
        self._game_var = tk.StringVar(value=current_display)
        game_menu = ttk.Combobox(
            frame, textvariable=self._game_var,
            values=pack_display, state="readonly", width=26,
        )
        game_menu.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- AI backend provider selector --------------------------------
        tk.Label(
            frame, text="AI Backend", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        _claude_available = is_claude_available()
        _provider_options = [AiProvider.GEMINI.value]
        if _claude_available:
            _provider_options.append(AiProvider.CLAUDE.value)

        current_provider_raw = self._current.get(
            "active_ai_provider", AiProvider.GEMINI.value
        )
        # if Claude saved but extras now absent, fall back to Gemini
        if current_provider_raw == AiProvider.CLAUDE.value and not _claude_available:
            current_provider_raw = AiProvider.GEMINI.value

        self._provider_var = tk.StringVar(value=current_provider_raw)
        self._provider_combo = ttk.Combobox(
            frame, textvariable=self._provider_var,
            values=_provider_options, state="readonly", width=18,
        )
        self._provider_combo.grid(row=row, column=1, sticky="w", pady=6)

        if not _claude_available:
            self._provider_note = tk.Label(
                frame,
                text="Claude hidden — install [claude] extras to enable",
                bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
            )
            self._provider_note.grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
            row += 1
        row += 1

        # -- AI model combobox — content switches per provider -----------
        tk.Label(
            frame, text="AI Model", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        # determine starting model from saved settings
        _initial_provider = AiProvider(self._provider_var.get())
        if _initial_provider == AiProvider.GEMINI:
            _initial_model = self._current.get("gemini_model", "gemini-2.5-flash")
        else:
            _initial_model = self._current.get("claude_model", "claude-sonnet-4-6")

        self._model_var = tk.StringVar(value=_initial_model)
        self._model_combo = ttk.Combobox(
            frame, textvariable=self._model_var,
            values=[_initial_model], state="readonly", width=26,
        )
        self._model_combo.grid(row=row, column=1, sticky="w", pady=6)

        self._model_status = tk.Label(
            frame, text="",
            bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
        )
        self._model_status.grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
        row += 2

        # bind provider change to refresh model list
        self._provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)

        # kick off initial model fetch for starting provider
        self.after(100, self._refresh_model_list)

        # -- theme picker ------------------------------------------------
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

        # -- cooldown ----------------------------------------------------
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

        # -- advisor input source ----------------------------------------
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

        # -- grid overlay toggle -----------------------------------------
        tk.Label(
            frame, text="Grid overlay", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._grid_var = tk.BooleanVar(
            value=bool(self._current.get("grid_overlay_enabled", True))
        )
        grid_check = ttk.Checkbutton(
            frame,
            text="Draw coordinate grid on placement screenshots",
            variable=self._grid_var,
        )
        grid_check.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- floating advice toggle (v0.8.0.1) ---------------------------
        tk.Label(
            frame, text="Floating advice", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._floating_advice_var = tk.BooleanVar(
            value=bool(self._current.get("show_floating_advice_when_hidden", True))
        )
        floating_check = ttk.Checkbutton(
            frame,
            text="Show in floating window when overlay is hidden",
            variable=self._floating_advice_var,
        )
        floating_check.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- API keys (v0.8.1.1) -----------------------------------------
        separator_keys = ttk.Separator(frame, orient=tk.HORIZONTAL)
        separator_keys.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 8))
        row += 1

        tk.Label(
            frame, text="Gemini API key", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 16))

        # populate from keyring; displayed masked
        _gemini_key_stored = keyring.get_password("gassi", "gemini_api_key") or ""
        self._gemini_key_var = tk.StringVar(value=_gemini_key_stored)
        gemini_key_entry = ttk.Entry(
            frame, textvariable=self._gemini_key_var,
            show="*", width=30,
        )
        gemini_key_entry.grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        tk.Label(
            frame, text="Claude API key", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 16))

        _claude_key_stored = keyring.get_password("gassi", "claude_api_key") or ""
        self._claude_key_var = tk.StringVar(value=_claude_key_stored)
        claude_key_entry = ttk.Entry(
            frame, textvariable=self._claude_key_var,
            show="*", width=30,
        )
        claude_key_entry.grid(row=row, column=1, sticky="w", pady=4)

        tk.Label(
            frame,
            text="Keys stored in OS keyring — never written to disk.",
            bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
        ).grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
        row += 2

        # -- calibration -------------------------------------------------
        if self._calibration_service is not None:
            separator = ttk.Separator(frame, orient=tk.HORIZONTAL)
            separator.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 8))
            row += 1

            calib_frame = tk.Frame(frame, bg=t.bg_primary)
            calib_frame.grid(row=row, column=0, columnspan=2, sticky="w")

            tk.Label(
                calib_frame,
                text="Auto-detect HUD regions from a live screenshot.",
                bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
            ).pack(anchor="w")

            tk.Button(
                calib_frame, text="Calibrate HUD",
                bg=t.bg_header, fg=t.fg_accent,
                font=t.font("normal", bold=True),
                bd=0, activebackground=t.bg_button_hover,
                cursor="hand2", padx=10, pady=4,
                command=self._open_calibration_dialog,
            ).pack(anchor="w", pady=(6, 0))
            row += 1

        frame.columnconfigure(1, weight=1)
        return frame

    def _on_provider_changed(self, _event: Any = None) -> None:
        """Refresh model list when the backend provider combobox changes."""
        self._model_status.config(text="")
        self._model_combo.config(values=[])
        self._model_var.set("")
        self._refresh_model_list()

    def _refresh_model_list(self) -> None:
        """Populate model combobox based on the currently selected provider."""
        provider_str = self._provider_var.get()
        try:
            provider = AiProvider(provider_str)
        except ValueError:
            provider = AiProvider.GEMINI

        t = self._theme

        if provider == AiProvider.CLAUDE:
            models = fetch_available_claude_models()
            current = self._current.get("claude_model", models[0] if models else "")
            if current not in models:
                models = [current] + models
            self._model_combo.config(values=models, state="readonly")
            self._model_var.set(current if current in models else models[0])
            self._model_status.config(
                text=f"✓ {len(models)} models (static list)",
                fg=t.fg_accent,
            )
        else:
            # Gemini: live fetch
            current = self._current.get("gemini_model", "gemini-2.5-flash")
            self._model_var.set(current)
            self._model_combo.config(values=[current], state="readonly")
            self._model_status.config(
                text="Fetching models...", fg=t.fg_dim,
            )
            if self._api_key:
                self.after(0, self._fetch_gemini_models)
            else:
                from gassi.core.ai.gemini_backend import _FALLBACK_MODELS  # noqa: PLC0415
                self._model_combo.config(values=_FALLBACK_MODELS)
                self._model_status.config(
                    text="No Gemini API key — using fallback list",
                    fg=t.fg_warning,
                )

    def _open_calibration_dialog(self) -> None:
        from gassi.views.calibration_dialog import CalibrationDialog  # noqa: PLC0415
        CalibrationDialog(
            parent=self,
            theme=self._theme,
            calibration_service=self._calibration_service,  # type: ignore[arg-type]
            game_id=self._game_id,
        )

    def _fetch_gemini_models(self) -> None:
        """Fetch available Gemini models and populate the combobox."""
        def _on_done(models: list[str]) -> None:
            self.after(0, lambda: self._update_model_combo(models))

        def _on_error(_msg: str) -> None:
            from gassi.core.ai.gemini_backend import _FALLBACK_MODELS  # noqa: PLC0415
            self.after(0, lambda: self._update_model_combo(
                _FALLBACK_MODELS, error=True
            ))

        fetch_available_models(self._api_key, _on_done, _on_error)

    def _update_model_combo(
        self, models: list[str], error: bool = False
    ) -> None:
        """Update combobox values after background fetch completes."""
        try:
            current = self._model_var.get()
            # ensure current selection is in the list
            if current not in models:
                models = [current] + models
            self._model_combo.config(values=models, state="readonly")
            # keep current selection if still valid, else default
            if current in models:
                self._model_var.set(current)
            else:
                self._model_var.set(models[0])

            t = self._theme
            if error:
                self._model_status.config(
                    text="Fetch failed — showing fallback models",
                    fg=t.fg_warning,
                )
            else:
                self._model_status.config(
                    text=f"✓ {len(models)} models available",
                    fg=t.fg_accent,
                )
        except tk.TclError:
            pass  # dialog was closed before fetch completed

    def _save(self) -> None:
        """Collect all settings, persist to JSON and keyring, notify caller."""
        settings: dict[str, Any] = {}

        # hotkeys
        for key, capture in self._hotkey_captures.items():
            settings[key] = capture.value

        # general
        settings["theme_name"] = self._theme_var.get()
        settings["cooldown_seconds"] = self._cooldown_var.get()
        settings["advisor_input_source"] = self._source_var.get()
        settings["grid_overlay_enabled"] = self._grid_var.get()
        settings["show_floating_advice_when_hidden"] = self._floating_advice_var.get()
        settings["active_game_id"] = self._game_display_to_id.get(
            self._game_var.get(), self._game_var.get()
        )

        # provider + model — save both model keys so switching back
        # preserves the previously chosen model for each provider
        provider_str = self._provider_var.get()
        settings["active_ai_provider"] = provider_str
        selected_model = self._model_var.get()
        try:
            provider = AiProvider(provider_str)
        except ValueError:
            provider = AiProvider.GEMINI
        if provider == AiProvider.CLAUDE:
            settings["claude_model"] = selected_model
            settings["gemini_model"] = self._current.get("gemini_model", "gemini-2.5-flash")
        else:
            settings["gemini_model"] = selected_model
            settings["claude_model"] = self._current.get("claude_model", "claude-sonnet-4-6")

        save_settings(settings)

        # persist API keys to OS keyring — write only if non-empty and changed
        _new_gemini_key = self._gemini_key_var.get().strip()
        if _new_gemini_key:
            _stored_gemini = keyring.get_password("gassi", "gemini_api_key") or ""
            if _new_gemini_key != _stored_gemini:
                keyring.set_password("gassi", "gemini_api_key", _new_gemini_key)

        _new_claude_key = self._claude_key_var.get().strip()
        if _new_claude_key:
            _stored_claude = keyring.get_password("gassi", "claude_api_key") or ""
            if _new_claude_key != _stored_claude:
                keyring.set_password("gassi", "claude_api_key", _new_claude_key)

        self._on_save(settings)
        self.destroy()

    def _center_on_parent(self, parent: tk.Tk) -> None:
        parent.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - self._WIDTH) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self._HEIGHT) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")
