"""Game pack manifest and HUD region definitions."""

from pydantic import BaseModel, Field


class HudRegion(BaseModel):
    """A pre-calibrated screen region for OCR/screenshot capture.

    Coordinates are fractional (0.0–1.0) relative to the captured window,
    so they survive resolution and UI-scale changes without recalibration.
    """

    label: str
    x_pct: float = Field(ge=0.0, le=1.0)
    y_pct: float = Field(ge=0.0, le=1.0)
    width_pct: float = Field(ge=0.0, le=1.0)
    height_pct: float = Field(ge=0.0, le=1.0)


class GamePackManifest(BaseModel):
    """Metadata and configuration for a single game pack.

    Loaded from game_packs/<game_id>/manifest.yaml at startup.
    All optional fields default safely so existing packs don’t need updating.
    """

    game_id: str
    display_name: str
    window_title_pattern: str
    game_version: str
    hud_regions: list[HudRegion] = Field(default_factory=list)
    quick_prompts: list[str] = Field(default_factory=list)

    # v0.5.0: RAG pipeline — points to a Chroma collection name.
    # None = use static prompt text (current default for all packs).
    rag_collection_name: str | None = None

    # v0.5.0: per-game RAG chunk count override (default used if None)
    rag_top_k: int | None = None

    # v0.5.0: minimum game version for RAG collection compatibility.
    # If game patches change mechanics significantly, old chunks can be filtered.
    rag_min_game_version: str | None = None

    # v0.5.12: preferred advisor input source for this pack.
    # None = use global settings default. Values: "ocr", "screenshot".
    preferred_advisor_source: str | None = None

    # v0.7.0: native window detection — OS-specific window class or process name.
    # Used by NativeWindowRegionProvider when implemented.
    # Example: "UnityWndClass" (Timberborn), "Nebuchadnezzar" (Win32 class)
    window_class: str | None = None

    # v0.7.1: anti-cheat compatibility note for this game.
    # Displayed in settings or logs if set. Pure informational.
    anticheat_note: str | None = None

    # v0.7.2: preferred AI backend for this pack.
    # None = use global Settings selection. Values: "gemini", "claude".
    # Informational hint only — Settings always wins (AD-26).
    preferred_backend: str | None = None
