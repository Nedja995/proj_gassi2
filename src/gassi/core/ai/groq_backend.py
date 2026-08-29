"""Groq cloud AI backend (v0.9.4).

Groq provides fast inference for open-weight models (Llama, Mixtral,
Gemma) via an OpenAI-compatible API with a generous free tier.

Free tier (as of mid-2026):
    14,400 requests/day, 6,000 tokens/minute — sufficient for casual use.
    Rate limit error (429) surfaces a readable message via base class handler.

Requires the optional [providers] extras:
    uv sync --extra providers

API key:
    Register at https://console.groq.com — free, no credit card required.
    Store via Settings dialog (saved to OS keyring under "groq_api_key").

Vision models:
    llama-3.2-11b-vision-preview  — recommended, free tier, good quality
    llama-3.2-90b-vision-preview  — higher quality, hits rate limits faster

Text-only models (OCR advisor path only):
    llama-3.1-8b-instant   — very fast, low latency
    llama-3.3-70b-versatile — highest text quality on free tier
"""

import logging

from gassi.core.ai.openai_compat_backend import OpenAiCompatBackend

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Static model list — Groq has a stable, curated set.
# Ordered: vision-capable first (primary use case), text-only after.
GROQ_MODELS: list[str] = [
    "llama-3.2-11b-vision-preview",   # vision — free tier, recommended
    "llama-3.2-90b-vision-preview",   # vision — higher quality, rate-limited
    "llama-3.3-70b-versatile",        # text-only — best reasoning on free tier
    "llama-3.1-8b-instant",           # text-only — fastest, lowest latency
    "mixtral-8x7b-32768",             # text-only — strong reasoning, 32k context
]

_DEFAULT_MODEL = "llama-3.2-11b-vision-preview"


class GroqBackend(OpenAiCompatBackend):
    """Groq cloud inference backend.

    Fast OpenAI-compatible inference for Llama and other open-weight models.
    Free tier with generous daily limits — no credit card required.
    """

    _provider_name = "Groq"
    _base_url = _GROQ_BASE_URL

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        """Initialise the Groq backend.

        Args:
            api_key: Groq API key from https://console.groq.com.
                     Retrieved from OS keyring by factory; never stored in config.
            model:   Model identifier. AppSettings.groq_model feeds this at runtime.
        """
        self._api_key = api_key
        self._model = model
        super().__init__()
        logger.info("GroqBackend: model=%s", self._model)


def fetch_available_groq_models() -> list[str]:
    """Return the static list of known Groq models.

    Groq's model list is curated and stable. Returns vision models first
    (primary GASSI use case), text-only models after.
    """
    return list(GROQ_MODELS)
