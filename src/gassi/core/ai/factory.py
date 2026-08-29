"""AI backend factory — constructs the correct AiBackend from AppSettings.

Single point of knowledge about which provider requires which key and
which backend class. ViewModel and main.py never import backend classes
directly — they use build_ai_backend() exclusively.

Provider availability:
    Gemini:      always available (google-genai in core deps)
    Claude:      optional [claude] extras (anthropic SDK)
    Ollama:      optional [providers] extras (openai SDK) + local Ollama server
    Groq:        optional [providers] extras (openai SDK) + Groq API key
    Together:    optional [providers] extras (openai SDK) + Together AI key
    HuggingFace: optional [providers] extras (openai SDK) + HF API token

Keyring key names (service="gassi"):
    gemini_api_key, claude_api_key, groq_api_key,
    together_api_key, huggingface_api_key
    Ollama has no key (local server, auth optional via ollama_base_url).

preferred_backend from GamePackManifest:
    This factory never reads manifest.preferred_backend. That field is
    informational only — logged at startup by main.py. Settings always wins.
"""

import logging
from typing import TYPE_CHECKING

from gassi.models.config import AppSettings
from gassi.models.enums import AiProvider

if TYPE_CHECKING:
    from gassi.core.ai.protocol import AiBackend

logger = logging.getLogger(__name__)

# Keyring credentials
_KEYRING_SERVICE = "gassi"

# Maps each provider that requires a key to its keyring username.
# Ollama is absent — local server, no API key required.
_PROVIDER_KEYRING_USERNAME: dict[AiProvider, str] = {
    AiProvider.GEMINI:       "gemini_api_key",
    AiProvider.CLAUDE:       "claude_api_key",
    AiProvider.GROQ:         "groq_api_key",
    AiProvider.TOGETHER:     "together_api_key",
    AiProvider.HUGGINGFACE:  "huggingface_api_key",
}


def get_api_key(provider: AiProvider) -> str | None:
    """Retrieve the API key for the given provider from OS keyring.

    Returns None if the provider has no key (Ollama) or if no key is stored.
    Callers decide how to handle absence.
    """
    import keyring  # noqa: PLC0415

    username = _PROVIDER_KEYRING_USERNAME.get(provider)
    if username is None:
        return None  # local provider — no key needed
    return keyring.get_password(_KEYRING_SERVICE, username)


def build_ai_backend(settings: AppSettings, api_key: str) -> "AiBackend":
    """Construct and return the AiBackend for the active provider.

    Args:
        settings: current AppSettings — reads active_ai_provider and the
                  per-provider model fields (gemini_model, claude_model, etc.).
        api_key:  the API key for the active provider, already retrieved from
                  keyring by the caller. Empty string / None for Ollama.

    Returns:
        An AiBackend Protocol-compliant instance.

    Raises:
        ImportError: if the required extras are not installed.
        ValueError:  if an unknown provider is configured.
    """
    provider = settings.active_ai_provider

    if provider == AiProvider.GEMINI:
        from gassi.core.ai.gemini_backend import GeminiBackend  # noqa: PLC0415
        backend = GeminiBackend(api_key=api_key, model=settings.gemini_model)
        logger.info("AI backend: Gemini (%s)", settings.gemini_model)
        return backend

    if provider == AiProvider.CLAUDE:
        _require_providers_extras("[claude]", "anthropic", "uv sync --extra claude")
        from gassi.core.ai.claude_backend import ClaudeBackend  # noqa: PLC0415
        backend = ClaudeBackend(api_key=api_key, model=settings.claude_model)
        logger.info("AI backend: Claude (%s)", settings.claude_model)
        return backend

    if provider == AiProvider.OLLAMA:
        _require_providers_extras("[providers]", "openai", "uv sync --extra providers")
        from gassi.core.ai.ollama_backend import OllamaBackend  # noqa: PLC0415
        backend = OllamaBackend(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        logger.info("AI backend: Ollama (%s @ %s)", settings.ollama_model, settings.ollama_base_url)
        return backend

    if provider == AiProvider.GROQ:
        _require_providers_extras("[providers]", "openai", "uv sync --extra providers")
        from gassi.core.ai.groq_backend import GroqBackend  # noqa: PLC0415
        backend = GroqBackend(api_key=api_key, model=settings.groq_model)
        logger.info("AI backend: Groq (%s)", settings.groq_model)
        return backend

    if provider == AiProvider.TOGETHER:
        _require_providers_extras("[providers]", "openai", "uv sync --extra providers")
        from gassi.core.ai.together_backend import TogetherBackend  # noqa: PLC0415
        backend = TogetherBackend(api_key=api_key, model=settings.together_model)
        logger.info("AI backend: Together AI (%s)", settings.together_model)
        return backend

    if provider == AiProvider.HUGGINGFACE:
        _require_providers_extras("[providers]", "openai", "uv sync --extra providers")
        from gassi.core.ai.huggingface_backend import HuggingFaceBackend  # noqa: PLC0415
        backend = HuggingFaceBackend(api_key=api_key, model=settings.huggingface_model)
        logger.info("AI backend: HuggingFace (%s)", settings.huggingface_model)
        return backend

    raise ValueError(f"Unknown AiProvider: {provider!r}")


def _require_providers_extras(group: str, package: str, install_cmd: str) -> None:
    """Raise ImportError with a clear install hint if a required package is absent."""
    try:
        __import__(package)
    except ImportError as exc:
        raise ImportError(
            f"{group} extras are required for this provider but are not installed.\n"
            f"Install with: {install_cmd}"
        ) from exc


# ---------------------------------------------------------------------------
# Availability helpers — used by Settings UI to hide unavailable providers
# ---------------------------------------------------------------------------

def is_claude_available() -> bool:
    """Return True if the [claude] extras (anthropic SDK) are installed."""
    try:
        import anthropic  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False


def is_providers_available() -> bool:
    """Return True if the [providers] extras (openai SDK) are installed.

    When True, Ollama / Groq / Together / HuggingFace are all available
    — they share the same dep group.
    """
    try:
        import openai  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False
