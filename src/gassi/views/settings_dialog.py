"""Settings dialog — configurable hotkeys, theme, cooldown, AI provider/model.

Accessible via gear icon in the toolbar. All changes are saved to a
persistent JSON config and applied immediately where possible.
Hotkey changes require an app restart to take effect (pynput limitation).

Provider support (v0.9.5):
    All six AI providers are listed in the backend selector. Providers that
    require optional extras ([claude], [providers]) are shown with a note
    when the extras are absent — they are never hidden entirely, so the user
    knows they exist and how to enable them.

    Provider tiers displayed in the dropdown:
        [Local]         — Ollama (no key, configurable URL)
        [Cloud — free]  — Groq, Together AI, HuggingFace Inference API
        [Cloud — paid]  — Gemini, Claude

    Ollama model list: fetched live from /api/tags (background thread).
    Falls back to OLLAMA_RECOMMENDED_MODELS when the server is unreachable.
    All other providers: static curated lists.

    Per-provider model selections are persisted independently so switching
    back to a provider restores the previously chosen model.

    API key fields: all cloud providers show a masked entry that reads from
    and writes to the OS keyring. Ollama shows a URL field instead.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

import keyring

from gassi.core.calibration_service import CalibrationService
from gassi.core.ai.gemini_backend import fetch_available_models as fetch_gemini_models
from gassi.core.ai.gemini_backend import _FALLBACK_MODELS as _GEMINI_FALLBACK
from gassi.core.ai.claude_backend import fetch_available_claude_models, CLAUDE_MODELS
from gassi.core.ai.groq_backend import fetch_available_groq_models
from gassi.core.ai.together_backend import fetch_available_together_models
from gassi.core.ai.huggingface_backend import fetch_available_huggingface_models
from gassi.core.ai.ollama_backend import (
    fetch_ollama_models,
    OLLAMA_RECOMMENDED_MODELS,
    OLLAMA_MODEL_VRAM,
)
from gassi.core.ai.factory import is_claude_available, is_providers_available
from gassi.core.game_pack_loader import GamePackLoader
from gassi.core.settings_manager import save_settings
from gassi.core.theme.theme import Theme, THEMES
from gassi.models.enums import AiProvider


# ---------------------------------------------------------------------------
# Provider display metadata
# ---------------------------------------------------------------------------

# Human-readable label shown in the provider combobox.
_PROVIDER_DISPLAY: dict[AiProvider, str] = {
    AiProvider.GEMINI:       "Gemini [Cloud — paid]",
    AiProvider.CLAUDE:       "Claude [Cloud — paid]",
    AiProvider.OLLAMA:       "Ollama [Local]",
    AiProvider.GROQ:         "Groq [Cloud — free]",
    AiProvider.TOGETHER:     "Together AI [Cloud — free]",
    AiProvider.HUGGINGFACE:  "HuggingFace Inference API [Cloud — free]",
}

# Reverse lookup: display string -> AiProvider
_DISPLAY_TO_PROVIDER: dict[str, AiProvider] = {
    v: k for k, v in _PROVIDER_DISPLAY.items()
}

# Short install hint shown when a provider's extras are missing.
_PROVIDER_INSTALL_HINT: dict[AiProvider, str] = {
    AiProvider.CLAUDE:      "Requires: uv sync --extra claude",
    AiProvider.OLLAMA:      "Requires: uv sync --extra providers",
    AiProvider.GROQ:        "Requires: uv sync --extra providers",
    AiProvider.TOGETHER:    "Requires: uv sync --extra providers",
    AiProvider.HUGGINGFACE: "Requires: uv sync --extra providers",
}

# Keyring username per cloud provider (mirrors factory._PROVIDER_KEYRING_USERNAME).
_PROVIDER_KEYRING: dict[AiProvider, str] = {
    AiProvider.GEMINI:      "gemini_api_key",
    AiProvider.CLAUDE:      "claude_api_key",
    AiProvider.GROQ:        "groq_api_key",
    AiProvider.TOGETHER:    "together_api_key",
    AiProvider.HUGGINGFACE: "huggingface_api_key",
}

# Default model setting key per provider.
_PROVIDER_MODEL_SETTING: dict[AiProvider, str] = {
    AiProvider.GEMINI:      "gemini_model",
    AiProvider.CLAUDE:      "claude_model",
    AiProvider.OLLAMA:      "ollama_model",
    AiProvider.GROQ:        "groq_model",
    AiProvider.TOGETHER:    "together_model",
    AiProvider.HUGGINGFACE: "huggingface_model",
}

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
            display_parts.append(part.strip("<>").upper())
        else:
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
        top = self.winfo_toplevel()
        top.bind("<Key>", self._on_key_press)

    _SPECIAL_KEYS = frozenset({
        "f1", "f2", "f3", "f4", "f5", "f6",
        "f7", "f8", "f9", "f10", "f11", "f12",
        "space", "return", "escape", "tab", "backspace", "delete",
        "home", "end", "prior", "next",
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

        if event.state & 0x1:
            modifiers.append("<shift>")
        if event.state & 0x4:
            modifiers.append("<ctrl>")
        if event.state & 0x8 or event.state & 0x20000:
            modifiers.append("<alt>")

        if key_name in ("shift_l", "shift_r", "control_l", "control_r",
                        "alt_l", "alt_r", "super_l", "super_r"):
            self._capturing = True
            top.bind("<Key>", self._on_key_press)
            return

        if key_name in self._SPECIAL_KEYS:
            pynput_key = f"<{key_name}>"
        elif len(key_name) == 1:
            pynput_key = key_name
        else:
            pynput_key = f"<{key_name}>"

        if modifiers:
            self._value = "+".join(modifiers) + "+" + pynput_key
        else:
            self._value = pynput_key

        t = self._theme
        self._display_label.config(text=_display_hotkey(self._value), fg=t.fg_text)
        self._capture_btn.config(text="Set", state=tk.NORMAL)


class SettingsDialog(tk.Toplevel):
    """Modal settings dialog with Hotkeys and General tabs.

    v0.9.5: All six AI providers available in the backend selector.
    Provider combobox shows tier labels. Model picker and credential
    section update dynamically per selected provider. Ollama shows a
    URL field; all cloud providers show a masked API key entry.
    """

    _WIDTH = 480
    _HEIGHT = 740  # v0.9.7: +20px for native window detection toggle

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
        anticheat_note: str = "",
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._on_save = on_save
        self._current = current_settings
        self._calibration_service = calibration_service
        self._game_id = game_id
        self._api_key = api_key           # Gemini key — kept for CalibrationService
        self._claude_api_key = claude_api_key
        self._pack_loader = pack_loader
        self._anticheat_note = anticheat_note
        t = theme

        self.title("GASSI — Settings")
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(bg=t.bg_primary)
        self.transient(parent)
        self.grab_set()

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

        self._hotkeys_frame = self._build_hotkeys_tab(notebook, t)
        self._general_frame = self._build_general_tab(notebook, t)

        notebook.add(self._hotkeys_frame, text="  Hotkeys  ")
        notebook.add(self._general_frame, text="  General  ")

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

    # ------------------------------------------------------------------
    # Hotkeys tab
    # ------------------------------------------------------------------

    def _build_hotkeys_tab(self, parent: tk.Widget, t: Theme) -> tk.Frame:
        frame = tk.Frame(parent, bg=t.bg_primary, padx=16, pady=16)

        hotkey_defs = [
            ("Advisor (query)", "hotkey_advisor_toggle"),
            ("Switch source",   "hotkey_advisor_source_switch"),
            ("Placement",       "hotkey_placement"),
            ("Lock overlay",    "hotkey_lock_overlay"),
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

            capture = HotkeyCapture(frame, t, self._current.get(key, ""))
            capture.grid(row=i, column=1, sticky="w", pady=6)
            self._hotkey_captures[key] = capture

        frame.columnconfigure(1, weight=1)
        return frame

    # ------------------------------------------------------------------
    # General tab
    # ------------------------------------------------------------------

    def _build_general_tab(self, parent: tk.Widget, t: Theme) -> tk.Frame:
        frame = tk.Frame(parent, bg=t.bg_primary, padx=16, pady=16)
        row = 0

        # -- active game pack -------------------------------------------
        tk.Label(
            frame, text="Active game", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        current_game = self._current.get("active_game_id", "timberborn")
        if self._pack_loader is not None:
            packs = self._pack_loader.list_available_packs()
            pack_display = [d for _, d in packs]
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
        ttk.Combobox(
            frame, textvariable=self._game_var,
            values=pack_display, state="readonly", width=26,
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- anti-cheat note (v0.8.2) ----------------------------------
        if self._anticheat_note:
            tk.Label(
                frame, text="Anti-cheat", bg=t.bg_primary, fg=t.fg_text,
                font=t.font("normal"),
            ).grid(row=row, column=0, sticky="nw", pady=6, padx=(0, 16))
            tk.Label(
                frame, text=self._anticheat_note,
                bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
                wraplength=self._WIDTH - 140, justify=tk.LEFT,
            ).grid(row=row, column=1, sticky="w", pady=6)
            row += 1

        # -- hide from capture (v0.8.2) ---------------------------------
        tk.Label(
            frame, text="Hide from capture", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._hide_capture_var = tk.BooleanVar(
            value=bool(self._current.get("hide_from_capture", True))
        )
        ttk.Checkbutton(
            frame,
            text="Hide overlay from OBS and game capture (Win10 2004+ only)",
            variable=self._hide_capture_var,
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- separator before provider section -------------------------
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(8, 10),
        )
        row += 1

        # -- AI backend provider selector ------------------------------
        _claude_ok = is_claude_available()
        _providers_ok = is_providers_available()

        tk.Label(
            frame, text="AI Backend", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        # Build provider display list — all six always shown so user
        # knows they exist; unavailable ones are selectable but show a
        # hint on selection prompting installation.
        all_provider_displays = [_PROVIDER_DISPLAY[p] for p in AiProvider]

        current_provider = AiProvider(
            self._current.get("active_ai_provider", AiProvider.GEMINI.value)
        )
        self._provider_var = tk.StringVar(
            value=_PROVIDER_DISPLAY[current_provider]
        )
        self._provider_combo = ttk.Combobox(
            frame, textvariable=self._provider_var,
            values=all_provider_displays, state="readonly", width=34,
        )
        self._provider_combo.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # Install hint — shown/hidden dynamically by _refresh_provider_ui
        self._install_hint_label = tk.Label(
            frame, text="",
            bg=t.bg_primary, fg=t.fg_warning, font=t.font("small"),
            wraplength=self._WIDTH - 140, justify=tk.LEFT,
        )
        self._install_hint_label.grid(row=row, column=1, sticky="w", pady=(0, 4))
        row += 1

        # -- AI model combobox -----------------------------------------
        tk.Label(
            frame, text="AI Model", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        _initial_model = self._current.get(
            _PROVIDER_MODEL_SETTING.get(current_provider, "gemini_model"),
            "",
        )
        self._model_var = tk.StringVar(value=_initial_model)
        self._model_combo = ttk.Combobox(
            frame, textvariable=self._model_var,
            values=[_initial_model] if _initial_model else [],
            state="readonly", width=34,
        )
        self._model_combo.grid(row=row, column=1, sticky="w", pady=6)

        self._model_status = tk.Label(
            frame, text="",
            bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
        )
        self._model_status.grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
        row += 2

        # -- Ollama URL field (shown only for Ollama provider) ----------
        self._ollama_url_label = tk.Label(
            frame, text="Ollama URL", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        )
        self._ollama_url_var = tk.StringVar(
            value=self._current.get("ollama_base_url", "http://localhost:11434")
        )
        self._ollama_url_entry = ttk.Entry(
            frame, textvariable=self._ollama_url_var, width=30,
        )
        self._ollama_url_row = row
        # placed but visibility managed by _refresh_provider_ui
        self._ollama_url_label.grid(
            row=row, column=0, sticky="w", pady=4, padx=(0, 16)
        )
        self._ollama_url_entry.grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        # -- API key field (shown only for cloud providers) -----------
        self._api_key_label = tk.Label(
            frame, text="API Key", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        )
        self._api_key_var = tk.StringVar()
        self._api_key_entry = ttk.Entry(
            frame, textvariable=self._api_key_var, show="*", width=30,
        )
        self._api_key_hint = tk.Label(
            frame,
            text="Stored in OS keyring — never written to disk.",
            bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
        )
        self._api_key_row = row
        self._api_key_label.grid(
            row=row, column=0, sticky="w", pady=4, padx=(0, 16)
        )
        self._api_key_entry.grid(row=row, column=1, sticky="w", pady=4)
        self._api_key_hint.grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
        row += 2

        # bind provider change
        self._provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)

        # -- separator before display settings -------------------------
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(8, 10),
        )
        row += 1

        # -- theme -------------------------------------------------------
        tk.Label(
            frame, text="Theme", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._theme_var = tk.StringVar(value=self._current.get("theme_name", "dark"))
        ttk.Combobox(
            frame, textvariable=self._theme_var,
            values=list(THEMES.keys()), state="readonly", width=18,
        ).grid(row=row, column=1, sticky="w", pady=6)
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
        tk.Scale(
            cooldown_frame, from_=5, to=60, orient=tk.HORIZONTAL,
            variable=self._cooldown_var, length=140,
            bg=t.bg_primary, fg=t.fg_text, highlightthickness=0,
            troughcolor=t.bg_input, activebackground=t.fg_accent,
            font=t.font("small"),
        ).pack(side=tk.LEFT)
        row += 1

        # -- advisor input source ----------------------------------------
        tk.Label(
            frame, text="Default input", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._source_var = tk.StringVar(
            value=self._current.get("advisor_input_source", "ocr")
        )
        ttk.Combobox(
            frame, textvariable=self._source_var,
            values=["ocr", "screenshot"], state="readonly", width=18,
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- grid overlay ------------------------------------------------
        tk.Label(
            frame, text="Grid overlay", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._grid_var = tk.BooleanVar(
            value=bool(self._current.get("grid_overlay_enabled", True))
        )
        ttk.Checkbutton(
            frame,
            text="Draw coordinate grid on placement screenshots",
            variable=self._grid_var,
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- floating advice (v0.8.0.1) ----------------------------------
        tk.Label(
            frame, text="Floating advice", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._floating_advice_var = tk.BooleanVar(
            value=bool(self._current.get("show_floating_advice_when_hidden", True))
        )
        ttk.Checkbutton(
            frame,
            text="Show in floating window when overlay is hidden",
            variable=self._floating_advice_var,
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- native window detection (v0.9.7) ----------------------------
        tk.Label(
            frame, text="Auto-detect window", bg=t.bg_primary, fg=t.fg_text,
            font=t.font("normal"),
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))

        self._native_window_var = tk.BooleanVar(
            value=bool(self._current.get("use_native_window_detection", False))
        )
        ttk.Checkbutton(
            frame,
            text="Find game window by title instead of overlay position (Windows only)",
            variable=self._native_window_var,
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # -- calibration -------------------------------------------------
        if self._calibration_service is not None:
            ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(12, 8),
            )
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

        # initial UI state for starting provider
        self.after(100, self._refresh_provider_ui)

        return frame

    # ------------------------------------------------------------------
    # Provider UI refresh
    # ------------------------------------------------------------------

    def _active_provider(self) -> AiProvider:
        """Return the currently selected AiProvider from the combobox."""
        display = self._provider_var.get()
        return _DISPLAY_TO_PROVIDER.get(display, AiProvider.GEMINI)

    def _on_provider_changed(self, _event: Any = None) -> None:
        """Called when user picks a different provider in the combobox."""
        self._model_status.config(text="")
        self._model_combo.config(values=[])
        self._model_var.set("")
        self._refresh_provider_ui()

    def _refresh_provider_ui(self) -> None:
        """Update model picker, credential section, and install hint for active provider."""
        provider = self._active_provider()
        t = self._theme

        _claude_ok = is_claude_available()
        _providers_ok = is_providers_available()

        # -- install hint ------------------------------------------------
        needs_claude = provider == AiProvider.CLAUDE and not _claude_ok
        needs_providers = (
            provider in AiProvider.openai_compat_providers() and not _providers_ok
        )

        if needs_claude or needs_providers:
            hint = _PROVIDER_INSTALL_HINT.get(provider, "")
            self._install_hint_label.config(text=hint)
        else:
            self._install_hint_label.config(text="")

        # -- Ollama URL vs API key field ---------------------------------
        is_ollama = provider == AiProvider.OLLAMA
        is_cloud = provider in AiProvider.cloud_providers()

        if is_ollama:
            self._ollama_url_label.grid()
            self._ollama_url_entry.grid()
            self._api_key_label.grid_remove()
            self._api_key_entry.grid_remove()
            self._api_key_hint.grid_remove()
        elif is_cloud:
            self._ollama_url_label.grid_remove()
            self._ollama_url_entry.grid_remove()
            self._api_key_label.grid()
            self._api_key_entry.grid()
            self._api_key_hint.grid()
            # load stored key for this provider into the masked field
            keyring_name = _PROVIDER_KEYRING.get(provider, "")
            stored_key = keyring.get_password("gassi", keyring_name) or "" if keyring_name else ""
            self._api_key_var.set(stored_key)
        else:
            self._ollama_url_label.grid_remove()
            self._ollama_url_entry.grid_remove()
            self._api_key_label.grid_remove()
            self._api_key_entry.grid_remove()
            self._api_key_hint.grid_remove()

        # -- model list --------------------------------------------------
        self._load_model_list(provider)

    def _load_model_list(self, provider: AiProvider) -> None:
        """Populate the model combobox for the given provider."""
        t = self._theme
        setting_key = _PROVIDER_MODEL_SETTING.get(provider, "gemini_model")
        current_model = self._current.get(setting_key, "")

        self._model_status.config(text="Loading models...", fg=t.fg_dim)
        self._model_combo.config(values=[], state="readonly")
        self._model_var.set(current_model)

        if provider == AiProvider.GEMINI:
            if self._api_key:
                self._model_status.config(text="Fetching models...", fg=t.fg_dim)
                fetch_gemini_models(
                    self._api_key,
                    on_done=lambda models: self.after(
                        0, lambda: self._set_model_list(models, current_model)
                    ),
                    on_error=lambda _: self.after(
                        0, lambda: self._set_model_list(
                            list(_GEMINI_FALLBACK), current_model, error=True
                        )
                    ),
                )
            else:
                self._set_model_list(list(_GEMINI_FALLBACK), current_model, error=False)
                self._model_status.config(
                    text="No Gemini key — using fallback list", fg=t.fg_warning,
                )

        elif provider == AiProvider.CLAUDE:
            models = fetch_available_claude_models()
            self._set_model_list(models, current_model)

        elif provider == AiProvider.OLLAMA:
            base_url = self._ollama_url_var.get().strip() or "http://localhost:11434"
            self._model_status.config(text="Fetching Ollama models...", fg=t.fg_dim)
            fetch_ollama_models(
                base_url,
                on_done=lambda models: self.after(
                    0, lambda: self._set_model_list(
                        models, current_model, vram_hint=True
                    )
                ),
                on_error=lambda _: self.after(
                    0, lambda: self._set_model_list(
                        list(OLLAMA_RECOMMENDED_MODELS), current_model,
                        error=True, vram_hint=True,
                    )
                ),
            )

        elif provider == AiProvider.GROQ:
            self._set_model_list(fetch_available_groq_models(), current_model)

        elif provider == AiProvider.TOGETHER:
            self._set_model_list(fetch_available_together_models(), current_model)

        elif provider == AiProvider.HUGGINGFACE:
            self._set_model_list(fetch_available_huggingface_models(), current_model)

    def _set_model_list(
        self,
        models: list[str],
        current: str,
        error: bool = False,
        vram_hint: bool = False,
    ) -> None:
        """Update the model combobox with a fetched or static model list."""
        try:
            if not models:
                models = [current] if current else ["(none)"]
            if current and current not in models:
                models = [current] + models

            self._model_combo.config(values=models, state="readonly")
            self._model_var.set(current if current in models else models[0])

            t = self._theme
            selected = self._model_var.get()

            if error:
                status_text = "Server unreachable — showing recommended models"
                status_fg = t.fg_warning
            else:
                status_text = f"✓ {len(models)} models available"
                status_fg = t.fg_accent

            # append VRAM annotation for Ollama if available
            if vram_hint and selected in OLLAMA_MODEL_VRAM:
                status_text = OLLAMA_MODEL_VRAM[selected]
                status_fg = t.fg_dim

            self._model_status.config(text=status_text, fg=status_fg)

            # update VRAM hint when Ollama model selection changes
            if vram_hint:
                self._model_combo.bind(
                    "<<ComboboxSelected>>",
                    lambda _e: self._update_vram_hint(),
                )
        except tk.TclError:
            pass  # dialog closed before async callback fired

    def _update_vram_hint(self) -> None:
        """Refresh VRAM annotation label when user picks a different Ollama model."""
        selected = self._model_var.get()
        t = self._theme
        if selected in OLLAMA_MODEL_VRAM:
            self._model_status.config(text=OLLAMA_MODEL_VRAM[selected], fg=t.fg_dim)
        else:
            self._model_status.config(text="", fg=t.fg_dim)

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def _open_calibration_dialog(self) -> None:
        from gassi.views.calibration_dialog import CalibrationDialog  # noqa: PLC0415
        CalibrationDialog(
            parent=self,
            theme=self._theme,
            calibration_service=self._calibration_service,  # type: ignore[arg-type]
            game_id=self._game_id,
        )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Collect all settings, persist to JSON and keyring, call on_save."""
        settings: dict[str, Any] = {}

        # hotkeys
        for key, capture in self._hotkey_captures.items():
            settings[key] = capture.value

        # display settings
        settings["theme_name"] = self._theme_var.get()
        settings["cooldown_seconds"] = self._cooldown_var.get()
        settings["advisor_input_source"] = self._source_var.get()
        settings["grid_overlay_enabled"] = self._grid_var.get()
        settings["show_floating_advice_when_hidden"] = self._floating_advice_var.get()
        settings["hide_from_capture"] = self._hide_capture_var.get()
        settings["use_native_window_detection"] = self._native_window_var.get()
        settings["active_game_id"] = self._game_display_to_id.get(
            self._game_var.get(), self._game_var.get()
        )

        # provider + per-provider model persistence
        provider = self._active_provider()
        settings["active_ai_provider"] = provider.value
        selected_model = self._model_var.get()

        # persist selected model under its own key; preserve all others
        for p, key in _PROVIDER_MODEL_SETTING.items():
            if p == provider:
                settings[key] = selected_model
            else:
                # carry forward previous value from current settings
                settings[key] = self._current.get(key, "")

        # Ollama URL
        settings["ollama_base_url"] = self._ollama_url_var.get().strip()

        save_settings(settings)

        # API key keyring persistence
        if provider in AiProvider.cloud_providers():
            keyring_name = _PROVIDER_KEYRING.get(provider, "")
            if keyring_name:
                new_key = self._api_key_var.get().strip()
                if new_key:
                    stored = keyring.get_password("gassi", keyring_name) or ""
                    if new_key != stored:
                        keyring.set_password("gassi", keyring_name, new_key)

        self._on_save(settings)
        self.destroy()

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def _center_on_parent(self, parent: tk.Tk) -> None:
        parent.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - self._WIDTH) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self._HEIGHT) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")
