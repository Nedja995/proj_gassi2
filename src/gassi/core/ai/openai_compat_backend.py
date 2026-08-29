"""OpenAI-compatible backend base class (v0.9.2).

Shared transport layer for all providers that implement the OpenAI
/v1/chat/completions REST API:
    Ollama      — local, no key, configurable base_url
    Groq        — cloud free tier, Bearer key
    Together AI — cloud free tier, Bearer key
    HuggingFace — Inference API cloud, Bearer token

Requires the optional [providers] extras:
    uv sync --extra providers

The openai SDK is imported at construction time (not module level) so
importing this module is safe without extras installed. Only instantiation
triggers the import — same deferred-import pattern as ClaudeBackend.

Structured output (placement mode response_schema):
    The openai SDK accepts a `response_format` parameter, but not all
    providers implement JSON schema enforcement reliably. JSON output is
    enforced via system prompt instruction (same approach as ClaudeBackend).
    The response_schema argument is accepted for Protocol compatibility and
    logged at DEBUG when provided. ViewModel._parse_placement_response()
    handles JSON extraction for all backends without changes.

Vision encoding:
    Images are sent as base64 data URIs in the `image_url` content block
    format — the standard OpenAI vision spec supported by all four providers.
    Format: `data:<mime_type>;base64,<b64data>`

Token usage:
    OpenAI-compat responses expose `usage.prompt_tokens` and
    `usage.completion_tokens`. Both fields are read via getattr with zero
    fallbacks — providers that omit usage (some Ollama builds) degrade
    gracefully to zero counts.

Rate-limit / error handling:
    HTTP 429 and provider-specific overload messages are caught by string
    matching and surfaced as readable RuntimeError with retry guidance.
    Same pattern as GeminiBackend and ClaudeBackend.
"""

import base64
import logging
from typing import Any

from gassi.models.results import UsageStats, estimate_cost

logger = logging.getLogger(__name__)

# Markers used for rate-limit / overload detection across all providers.
_RATE_LIMIT_MARKERS: tuple[str, ...] = (
    "429",
    "rate_limit",
    "rate limit",
    "too many requests",
    "quota",
    "resource_exhausted",
    "overloaded",
    "capacity",
)


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if the exception represents a rate-limit or overload response."""
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


def _build_rate_limit_error(provider_name: str, exc: Exception) -> RuntimeError:
    """Wrap a raw rate-limit error in a readable RuntimeError."""
    msg = (
        f"{provider_name} rate limit or server overload — "
        "wait a moment and try again."
    )
    logger.warning("%s rate-limit: %s", provider_name, exc)
    return RuntimeError(msg)


def _b64encode_image(image_bytes: bytes) -> str:
    """Base64-encode image bytes to a plain ASCII string (no line breaks)."""
    return base64.b64encode(image_bytes).decode("ascii")


class OpenAiCompatBackend:
    """Base class for all OpenAI-compatible AI provider backends.

    Subclasses must set:
        _provider_name: str   — human-readable name for logging and errors
        _base_url: str        — full base URL including /v1 path
        _api_key: str         — Bearer token; use a dummy string for Ollama
        _model: str           — model identifier for the provider

    Subclasses may override:
        _max_tokens: int      — default 1024; override for providers with
                                different limits or cost profiles
        _extra_headers: dict  — additional request headers (not needed by
                                most providers; reserved for future use)
    """

    _provider_name: str = "OpenAI-compat"
    _base_url: str = ""
    _api_key: str = ""
    _model: str = ""
    _max_tokens: int = 1024
    _extra_headers: dict[str, str] = {}  # noqa: RUF012

    def __init__(self) -> None:
        """Import openai SDK and construct the async client.

        Raises:
            ImportError: if the [providers] extras are not installed.
        """
        try:
            from openai import AsyncOpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "The [providers] extras are required for this backend.\n"
                "Install with: uv sync --extra providers"
            ) from exc

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        logger.debug(
            "%s backend initialised: model=%s base_url=%s",
            self._provider_name, self._model, self._base_url,
        )

    async def complete_text(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, UsageStats]:
        """Send a text-only prompt and return (response_text, usage_stats)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
            )
            text = _extract_text(response)
            usage = _extract_usage(response, self._model)
            return text, usage
        except Exception as exc:
            if _is_rate_limit_error(exc):
                raise _build_rate_limit_error(self._provider_name, exc) from exc
            raise

    async def complete_with_image(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        image_mime: str = "image/png",
        response_schema: Any | None = None,
    ) -> tuple[str, UsageStats]:
        """Send a prompt with an attached image and return (response_text, usage_stats).

        Image is encoded as a base64 data URI in the OpenAI vision content format.
        All four providers (Ollama, Groq, Together, HuggingFace) support this spec.

        Args:
            response_schema: Unused — JSON output enforced via system prompt
                instruction only (same approach as ClaudeBackend, AD-29).
                Accepted for AiBackend Protocol compatibility.
        """
        if response_schema is not None:
            logger.debug(
                "%s: response_schema provided but ignored — "
                "JSON output enforced via prompt instruction only",
                self._provider_name,
            )

        data_uri = f"data:{image_mime};base64,{_b64encode_image(image_bytes)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    },
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                ],
            },
        ]
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
            )
            text = _extract_text(response)
            usage = _extract_usage(response, self._model)
            return text, usage
        except Exception as exc:
            if _is_rate_limit_error(exc):
                raise _build_rate_limit_error(self._provider_name, exc) from exc
            raise


# ---------------------------------------------------------------------------
# Module-level helpers — used by the base class and subclasses
# ---------------------------------------------------------------------------

def _extract_text(response: Any) -> str:
    """Extract the assistant message text from an openai-compat response."""
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError) as exc:
        logger.warning("OpenAiCompatBackend: failed to extract text: %s", exc)
        return ""


def _extract_usage(response: Any, model: str) -> UsageStats:
    """Extract token counts from an openai-compat response.

    OpenAI-compat spec: response.usage.prompt_tokens / completion_tokens.
    Falls back to zero if the provider omits usage (some Ollama builds do).
    """
    try:
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    except Exception:  # noqa: BLE001
        input_tokens = 0
        output_tokens = 0

    cost = estimate_cost(model, input_tokens, output_tokens)
    stats = UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
    )
    logger.debug(
        "%s usage: in=%d out=%d cost=%s",
        model, input_tokens, output_tokens,
        f"${cost:.6f}" if cost is not None else "unknown",
    )
    return stats
