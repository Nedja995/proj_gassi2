"""AI backend factory — constructs the correct AiBackend from AppSettings.

Single point of knowledge about which provider requires which key and
which backend class. ViewModel and main.py never import backend classes
directly — they use build_ai_backend() exclusively.

Claude backend availability:
    ClaudeBackend is only constructed when AiProvider.CLAUDE is selected
    AND the [claude] extras are installed. If extras are absent, an
    ImportError is caught and re-raised with a clear installation hint.
    The Gemini backend has no optional extras — always available.

Keyring key names:
    Gemini: service="gassi", username="gemini_api_key"
    Claude: service="gassi", username="claude_api_key"

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
_GEMINI_USERNAME = "gemini_api_key"
_CLAUDE_USERNAME = "claude_api_key"


def get_api_key(provider: AiProvider) -> str | None:
    """Retrieve the API key for the given provider from OS keyring.

    Returns None if no key is stored — callers decide how to handle absence.
    """
    import keyring  # noqa: PLC0415

    username = _GEMINI_USERNAME if provider == AiProvider.GEMINI else _CLAUDE_USERNAME
    return keyring.get_password(_KEYRING_SERVICE, username)


def build_ai_backend(settings: AppSettings, api_key: str) -> "AiBackend":
    """Construct and return the AiBackend for the active provider.

    Args:
        settings: current AppSettings — reads active_ai_provider,
                  gemini_model, claude_model.
        api_key:  the API key for the active provider, already retrieved
                  from keyring by the caller.

    Returns:
        An AiBackend Protocol-compliant instance.

    Raises:
        ImportError: if AiProvider.CLAUDE is selected but the [claude]
                     extras are not installed.
        ValueError:  if an unknown provider is configured.
    """
    provider = settings.active_ai_provider

    if provider == AiProvider.GEMINI:
        from gassi.core.ai.gemini_backend import GeminiBackend  # noqa: PLC0415
        backend = GeminiBackend(api_key=api_key, model=settings.gemini_model)
        logger.info("AI backend: Gemini (%s)", settings.gemini_model)
        return backend

    if provider == AiProvider.CLAUDE:
        try:
            from gassi.core.ai.claude_backend import ClaudeBackend  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "ClaudeBackend selected but [claude] extras are not installed.\n"
                "Install with: uv sync --extra claude"
            ) from exc
        backend = ClaudeBackend(api_key=api_key, model=settings.claude_model)
        logger.info("AI backend: Claude (%s)", settings.claude_model)
        return backend

    raise ValueError(f"Unknown AiProvider: {provider!r}")


def is_claude_available() -> bool:
    """Return True if the [claude] extras (anthropic SDK) are installed."""
    try:
        import anthropic  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False
