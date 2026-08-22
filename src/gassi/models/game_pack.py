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
    """

    game_id: str
    display_name: str
    window_title_pattern: str
    game_version: str
    hud_regions: list[HudRegion] = Field(default_factory=list)

    # v2: will point to a Chroma collection; v1 uses static prompt text
    rag_collection_name: str | None = None
