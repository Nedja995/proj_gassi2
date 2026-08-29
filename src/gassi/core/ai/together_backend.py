"""Together AI cloud backend (v0.9.4).

Together AI provides hosted inference for a wide range of open-weight
models via an OpenAI-compatible API. Free tier available with credits
on signup; pay-as-you-go after.

Free tier (as of mid-2026):
    $1 credit on signup, then pay-per-token. Very cheap for small models.
    Rate limits are generous on paid tier; free tier may throttle.

Requires the optional [providers] extras:
    uv sync --extra providers

API key:
    Register at https://api.together.xyz — free credits on signup.
    Store via Settings dialog (saved to OS keyring under "together_api_key").

Vision models:
    meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo  — recommended, fast
    Qwen/Qwen2.5-VL-7B-Instruct                     — strong spatial reasoning
    Qwen/Qwen2.5-VL-72B-Instruct                    — highest quality vision

Text-only models:
    meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo  — fast, cheap
    meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo — high quality
"""

import logging

from gassi.core.ai.openai_compat_backend import OpenAiCompatBackend

logger = logging.getLogger(__name__)

_TOGETHER_BASE_URL = "https://api.together.xyz/v1"

# Static model list — vision-capable first, text-only after.
TOGETHER_MODELS: list[str] = [
    "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",   # vision — fast, recommended
    "Qwen/Qwen2.5-VL-7B-Instruct",                      # vision — strong spatial reasoning
    "Qwen/Qwen2.5-VL-72B-Instruct",                     # vision — highest quality
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",      # text-only — fast, cheap
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",     # text-only — high quality
]

_DEFAULT_MODEL = "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo"


class TogetherBackend(OpenAiCompatBackend):
    """Together AI cloud inference backend.

    Wide model selection, OpenAI-compatible API, pay-per-token pricing.
    Good alternative when Groq's free tier rate limits are hit.
    """

    _provider_name = "Together AI"
    _base_url = _TOGETHER_BASE_URL

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        """Initialise the Together AI backend.

        Args:
            api_key: Together AI API key from https://api.together.xyz.
                     Retrieved from OS keyring; never stored in config.
            model:   Model identifier. AppSettings.together_model feeds this at runtime.
        """
        self._api_key = api_key
        self._model = model
        super().__init__()
        logger.info("TogetherBackend: model=%s", self._model)


def fetch_available_together_models() -> list[str]:
    """Return the static list of recommended Together AI models.

    Together AI has hundreds of hosted models; this list is curated to
    the vision-capable and high-quality text models most relevant to GASSI.
    Vision models are listed first (primary use case).
    """
    return list(TOGETHER_MODELS)
