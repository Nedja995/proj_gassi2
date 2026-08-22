"""AI response result models."""

from pydantic import BaseModel, Field


class AdvisorResult(BaseModel):
    """Structured output from an Advisor mode query (OCR or screenshot).

    Both input sources (OCR text and screenshot image) resolve to this
    same model before any downstream logic — ViewModel never branches
    on input source past this point.
    """

    day: int | None = None
    season: str | None = None
    resources: dict[str, int] = Field(default_factory=dict)
    alerts: list[str] = Field(default_factory=list)
    advice: str = ""


class OcrResult(BaseModel):
    """Raw OCR extraction from a single HUD region."""

    text: str
    confidence: float
    region_label: str


class PlacementQuery(BaseModel):
    """Input data for a Placement mode request."""

    user_prompt: str
    capture_rect: tuple[int, int, int, int]  # x, y, w, h — screen coords
    scale_factor: float = 1.0  # unused in v1; required for v2 grid->pixel math


class PlacementResult(BaseModel):
    """Response from a Placement mode query.

    v1: free-text advice using landmarks/directions.
    v2: will add target_direction, target_offset_pct, confidence for
        grid-based coordinate rendering and arrow overlays.
    """

    advice_text: str

    # v2 additions (reserved, not populated in v1):
    target_direction: str | None = None
    target_offset_pct: tuple[float, float] | None = None
    confidence: float = 1.0
