"""HuggingFace Inference API backend (v0.9.4).

Targets the HuggingFace Inference API (serverless/cloud) ONLY.
Local HuggingFace inference via the `transformers` library is explicitly
NOT supported — it requires PyTorch, violating AD-06. That path is
tracked in vFuture and requires a deliberate AD decision to allow PyTorch.

The Inference API exposes an OpenAI-compatible endpoint at:
    https://api-inference.huggingface.co/v1/

Free tier (as of mid-2026):
    Rate-limited — the most restrictive of the free providers.
    Specific model availability depends on HuggingFace's serverless fleet.
    Models must be explicitly deployed for Inference API access.
    Check https://huggingface.co/models?pipeline_tag=image-text-to-text
    for models with "Hosted inference API" badge.

Requires the optional [providers] extras:
    uv sync --extra providers

API key (HF Access Token):
    Generate at https://huggingface.co/settings/tokens — free account required.
    Read-access token is sufficient. Store via Settings dialog
    (saved to OS keyring under "huggingface_api_key").

Vision models (confirmed Inference API availability, mid-2026):
    Qwen/Qwen2.5-VL-7B-Instruct   — strong vision + spatial reasoning
    meta-llama/Llama-3.2-11B-Vision-Instruct — good general vision

Text-only models:
    meta-llama/Meta-Llama-3.1-8B-Instruct  — fast, free tier friendly
    mistralai/Mistral-7B-Instruct-v0.3     — reliable, good reasoning

Note on reliability:
    HuggingFace Inference API serverless availability varies by model and
    server load. If a model returns a "model not loaded" or 503 error,
    switch to Groq or Together AI which have more stable free tiers.
"""

import logging

from gassi.core.ai.openai_compat_backend import OpenAiCompatBackend

logger = logging.getLogger(__name__)

_HUGGINGFACE_BASE_URL = "https://api-inference.huggingface.co/v1"

# Static model list — vision-capable first, text-only after.
# Only models confirmed to have Inference API support are listed.
HUGGINGFACE_MODELS: list[str] = [
    "Qwen/Qwen2.5-VL-7B-Instruct",                  # vision — strong, recommended
    "meta-llama/Llama-3.2-11B-Vision-Instruct",     # vision — good general purpose
    "meta-llama/Meta-Llama-3.1-8B-Instruct",        # text-only — fast, free-friendly
    "mistralai/Mistral-7B-Instruct-v0.3",            # text-only — reliable reasoning
]

_DEFAULT_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"


class HuggingFaceBackend(OpenAiCompatBackend):
    """HuggingFace Inference API (cloud/serverless) backend.

    Uses the OpenAI-compatible endpoint of the HuggingFace Inference API.
    This is a cloud provider — no local model files, no PyTorch required.

    Note: Free tier is rate-limited and model availability varies.
    Consider Groq or Together AI for more stable free-tier inference.
    """

    _provider_name = "HuggingFace"
    _base_url = _HUGGINGFACE_BASE_URL

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        """Initialise the HuggingFace Inference API backend.

        Args:
            api_key: HuggingFace Access Token from https://huggingface.co/settings/tokens.
                     Read-access token is sufficient.
                     Retrieved from OS keyring; never stored in config.
            model:   Model identifier (HuggingFace model repo path, e.g. "Qwen/Qwen2.5-VL-7B-Instruct").
                     AppSettings.huggingface_model feeds this at runtime.
        """
        self._api_key = api_key
        self._model = model
        super().__init__()
        logger.info("HuggingFaceBackend: model=%s", self._model)


def fetch_available_huggingface_models() -> list[str]:
    """Return the static list of recommended HuggingFace Inference API models.

    HuggingFace hosts thousands of models; only those confirmed to support
    the serverless Inference API with vision capability are listed.
    Vision models are listed first (primary GASSI use case).

    Note: Model availability changes as HuggingFace updates its hosted fleet.
    If a listed model returns 503 or "not loaded", try another from the list.
    """
    return list(HUGGINGFACE_MODELS)
