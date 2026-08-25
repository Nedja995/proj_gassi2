"""Claude AI backend implementation (Anthropic SDK).

Requires the optional [claude] extras:
    uv sync --extra claude

Structured output (placement mode response_schema) is enforced via
system prompt instruction + JSON parsing — Claude has no native schema
object equivalent to Gemini's types.Schema. The same
_parse_placement_response() fallback in the ViewModel handles both.

Rate-limit (429 / overloaded_error) handling mirrors GeminiBackend:
catches by string matching, surfaces a readable message with retry hint.

Import is deferred to _get_client() so importing this module is safe
even when the [claude] extras are not installed. Instantiation will
raise ImportError with a clear message if anthropic is missing.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Known Claude models — static list returned by fetch_available_claude_models().
# Anthropic has no public model-listing API endpoint.
# Ordered: cheapest/fastest first (Haiku), then Sonnet, then Opus.
CLAUDE_MODELS: list[str] = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
]

_DEFAULT_MODEL = "claude-sonnet-4-6"

# anthropic SDK error type strings used for rate-limit detection
_RATE_LIMIT_MARKERS = ("rate_limit_error", "overloaded_error", "529", "429")


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if exception is a rate-limit or overloaded error."""
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


def _build_rate_limit_error(exc: Exception) -> Exception:
    """Convert a raw rate-limit error into a readable RuntimeError."""
    msg = (
        "Claude API rate limit or overloaded — wait a moment and try again. "
        "Check https://console.anthropic.com for quota details."
    )
    logger.warning("Claude rate-limit: %s", exc)
    return RuntimeError(msg)


def _import_anthropic() -> Any:
    """Import and return the anthropic module, raising ImportError with guidance if absent."""
    try:
        import anthropic  # noqa: PLC0415
        return anthropic
    except ImportError as exc:
        raise ImportError(
            "The [claude] extras are required to use ClaudeBackend.\n"
            "Install with: uv sync --extra claude"
        ) from exc


class ClaudeBackend:
    """Anthropic Claude API backend.

    Implements the AiBackend Protocol — drop-in replacement for GeminiBackend.
    API key is retrieved from OS keyring at construction time, not stored in
    config files (same pattern as GeminiBackend).

    anthropic SDK is imported lazily inside _get_client() so the module can
    be safely imported without the [claude] extras installed. Only
    instantiation triggers the import.
    """

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._model = model
        self._api_key = api_key
        # Validate import at construction time — fail fast with a clear message.
        self._anthropic = _import_anthropic()
        self._client = self._anthropic.AsyncAnthropic(api_key=api_key)
        logger.debug("ClaudeBackend initialised: model=%s", self._model)

    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        """Send a text-only prompt to Claude and return the response text."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return _extract_text(response)
        except Exception as exc:
            if _is_rate_limit_error(exc):
                raise _build_rate_limit_error(exc) from exc
            raise

    async def complete_with_image(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        image_mime: str = "image/png",
        response_schema: Any | None = None,
    ) -> str:
        """Send a prompt with an attached image to Claude and return the response text.

        Args:
            response_schema: Unused by ClaudeBackend — Claude has no native schema
                object equivalent to Gemini's types.Schema. Structured JSON output
                is enforced via the system_prompt instruction already present in
                placement.txt. The ViewModel's _parse_placement_response() handles
                JSON extraction from the response text for both backends.
                Presence of response_schema is logged at debug level so mismatches
                can be detected during testing.
        """
        if response_schema is not None:
            logger.debug(
                "ClaudeBackend: response_schema provided but ignored — "
                "JSON output enforced via prompt instruction only"
            )

        image_content: dict[str, Any] = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_mime,
                "data": _b64encode(image_bytes),
            },
        }
        text_content: dict[str, Any] = {
            "type": "text",
            "text": user_prompt,
        }

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": [image_content, text_content]},
                ],
            )
            return _extract_text(response)
        except Exception as exc:
            if _is_rate_limit_error(exc):
                raise _build_rate_limit_error(exc) from exc
            raise


def _extract_text(response: Any) -> str:
    """Extract plain text from an Anthropic Message response object."""
    try:
        for block in response.content:
            if block.type == "text":
                return block.text or ""
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("ClaudeBackend: failed to extract text from response: %s", exc)
        return ""


def _b64encode(data: bytes) -> str:
    """Base64-encode bytes to a plain string (no line breaks)."""
    import base64  # noqa: PLC0415
    return base64.b64encode(data).decode("ascii")


def fetch_available_claude_models() -> list[str]:
    """Return the static list of known Claude models.

    Anthropic provides no public model-listing API endpoint, so this
    returns a hardcoded list ordered cheapest/fastest first.
    Callers should treat this list as advisory — model availability
    depends on the user's Anthropic plan.
    """
    return list(CLAUDE_MODELS)
