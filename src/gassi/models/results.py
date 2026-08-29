"""AI response result models."""

from pydantic import BaseModel, Field


class UsageStats(BaseModel):
    """Token usage and estimated cost for a single AI call.

    Populated by each AiBackend after a successful completion.
    Cost rates are hardcoded per known model string; None for unknown models.
    Session-level accumulation is done in AssistantViewModel.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# Cost per 1M tokens (input, output) by model string substring.
# Keys are matched via substring check — order matters (most specific first).
# Prices in USD as of mid-2026; update as providers change pricing.
# Local providers (Ollama) have no API cost — omitted from table.
# Free-tier providers (Groq) have $0 cost up to quota — modelled as zero.
_COST_TABLE: list[tuple[str, float, float]] = [
    # Gemini
    ("gemini-2.5-flash",       0.30,   1.00),
    ("gemini-3.1-flash-lite",  0.10,   0.40),
    ("gemini-3.5-flash",       0.30,   1.00),
    ("gemini-3.6-flash",       0.30,   1.00),
    ("gemini-2.5-pro",         1.25,   5.00),
    # Claude
    ("claude-haiku",           0.80,   4.00),
    ("claude-sonnet",          3.00,  15.00),
    ("claude-opus",           15.00,  75.00),
    # Groq (free tier — zero cost up to daily quota; $0 above quota not modelled)
    ("llama-3.2-11b-vision",   0.00,   0.00),
    ("llama-3.2-90b-vision",   0.00,   0.00),
    ("llama-3.3-70b",          0.00,   0.00),
    ("llama-3.1-8b",           0.00,   0.00),
    ("mixtral-8x7b",           0.00,   0.00),
    # Together AI (pay-per-token; prices as of mid-2026)
    ("llama-3.2-11b-vision-instruct-turbo",  0.18,  0.18),
    ("qwen2.5-vl-7b",                        0.30,  0.30),
    ("qwen2.5-vl-72b",                       0.90,  0.90),
    ("meta-llama-3.1-8b-instruct-turbo",     0.18,  0.18),
    ("meta-llama-3.1-70b-instruct-turbo",    0.88,  0.88),
    # HuggingFace Inference API (free tier; no published per-token price)
    ("qwen2.5-vl",             0.00,   0.00),
    ("llama-3.2-11b-vision-instruct",  0.00,  0.00),
    ("meta-llama-3.1-8b-instruct",     0.00,  0.00),
    ("mistral-7b",             0.00,   0.00),
]


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Return estimated USD cost for a call, or None if model is unknown."""
    model_lower = model.lower()
    for _key, _in_rate, _out_rate in _COST_TABLE:
        if _key in model_lower:
            return (
                input_tokens * _in_rate / 1_000_000
                + output_tokens * _out_rate / 1_000_000
            )
    return None


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
    v0.3.1: cell_reference populated when grid overlay is enabled.
    v0.3.2: target_direction, target_offset_pct used for canvas bounding box
            rendering once the transparent overlay layer is implemented.
    """

    advice_text: str

    # v0.3.1: grid cell reference returned by Gemini when grid is enabled
    cell_reference: str | None = None

    # v0.3.2 additions (reserved — canvas rendering deferred, see AD-23):
    target_direction: str | None = None
    target_offset_pct: tuple[float, float] | None = None
    confidence: float = 1.0
