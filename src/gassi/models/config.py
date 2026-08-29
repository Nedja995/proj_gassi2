"""Application configuration via pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings

from gassi.models.enums import AdvisorInputSource, AiProvider


class AppSettings(BaseSettings):
    """Root application settings.

    Values are loaded from environment variables prefixed with GASSI_
    (e.g. GASSI_GEMINI_MODEL) or from a .env file. API key is stored
    and retrieved via OS keyring, not here.
    """

    model_config = {"env_prefix": "GASSI_", "extra": "ignore"}

    # AI backend provider (v0.7.2 — extended v0.9.1)
    active_ai_provider: AiProvider = AiProvider.GEMINI

    # AI backend — model per provider
    # Each provider persists its last-used model independently so switching
    # back restores the prior selection (same pattern as gemini/claude, v0.7.2).
    gemini_model: str = "gemini-2.5-flash"
    claude_model: str = "claude-sonnet-4-6"
    # v0.9.x OpenAI-compatible providers
    ollama_model: str = "moondream2"
    groq_model: str = "llama-3.2-11b-vision-preview"
    together_model: str = "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo"
    huggingface_model: str = "Qwen/Qwen2.5-VL-7B-Instruct"

    # Ollama server URL — configurable for remote Ollama instances.
    # Default: localhost. Change to point at a network server or Docker container.
    ollama_base_url: str = "http://localhost:11434"

    # Advisor mode
    advisor_input_source: AdvisorInputSource = AdvisorInputSource.OCR
    cooldown_seconds: float = Field(default=15.0, ge=5.0, le=120.0)
    ocr_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    # Capture
    capture_resize_max_width: int = Field(default=1280, ge=640, le=3840)

    # Retry / backoff
    api_max_retries: int = Field(default=3, ge=1, le=10)
    api_backoff_seconds: float = Field(default=2.0, ge=0.5, le=30.0)
    api_cooldown_seconds: float = Field(default=30.0, ge=5.0, le=300.0)

    # Game pack
    active_game_id: str = "timberborn"

    # Theme
    theme_name: str = "dark"

    # TTS (optional, off by default)
    tts_enabled: bool = False
    tts_voice: str = "en-US-AriaNeural"

    # Hotkeys
    hotkey_advisor_toggle: str = "<f1>"
    hotkey_advisor_source_switch: str = "<shift>+<f1>"
    hotkey_placement: str = "<f2>"
    hotkey_lock_overlay: str = "<f3>"
    hotkey_debug_save_frame: str = "<f4>"

    # Grid overlay (v0.3.1)
    grid_overlay_enabled: bool = True
    grid_cols: int = Field(default=12, ge=4, le=26)   # A–L default (A–Z max)
    grid_rows: int = Field(default=8, ge=2, le=20)

    # Placement highlight (v0.3.2)
    placement_highlight_seconds: int = Field(default=8, ge=2, le=30)

    # Floating advice window (v0.8.0.1)
    # When overlay is offscreen and F1 fires, show advice in a centered floating window.
    show_floating_advice_when_hidden: bool = True
    floating_advice_timeout_seconds: int = Field(default=12, ge=4, le=60)

    # Anti-cheat posture (v0.8.2)
    # When True, SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) is applied to all
    # overlay windows at startup — hides them from OBS, game bar, and DirectX capture.
    # Requires Windows 10 build 19041+. Silently no-op on older Windows / non-Windows.
    hide_from_capture: bool = True

    # Native window detection (v0.9.7)
    # When True, use NativeWindowRegionProvider to auto-detect the game window
    # by title/class instead of deriving the capture rect from overlay geometry.
    # Windows-only in v0.9.7; falls back to overlay rect on other platforms.
    # Default False — opt-in, preserving existing manual positioning behaviour.
    use_native_window_detection: bool = False

    # Debug
    debug_log_max_lines: int = Field(default=200, ge=50, le=1000)
