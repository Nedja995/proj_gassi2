"""Gemini AI backend implementation.

Handles 429 RESOURCE_EXHAUSTED by reading the retryDelay from the
error response and surfacing a human-readable message with the wait time.
AFC is explicitly disabled since GASSI does not use function calling tools.
"""

import logging
import re
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai import types

from gassi.models.results import UsageStats, estimate_cost

logger = logging.getLogger(__name__)

# suppress AFC warning — we never use function calling tools
_AFC_CONFIG = types.AutomaticFunctionCallingConfig(disable=True)

_RETRY_DELAY_RE = re.compile(r"retry[^\d]*(\d+(?:\.\d+)?)\s*s", re.IGNORECASE)

# models shown in dropdown when API fetch fails
_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-2.5-pro",
]


def _parse_retry_seconds(error: Exception) -> float | None:
    """Extract retryDelay seconds from a 429 error message if present."""
    try:
        text = str(error)
        match = _RETRY_DELAY_RE.search(text)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


class GeminiBackend:
    """Google Gemini API backend.

    API key is retrieved from OS keyring at construction time,
    not stored in config files.
    """

    def __init__(self, api_key: str, model: str = "gemini-3.6-flash") -> None:
        self._model = model
        self._client = genai.Client(api_key=api_key)

    async def complete_text(self, system_prompt: str, user_prompt: str) -> tuple[str, UsageStats]:
        """Send text-only prompt to Gemini."""
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    automatic_function_calling=_AFC_CONFIG,
                ),
            )
            return response.text or "", _extract_usage(response, self._model)
        except Exception as exc:
            if _is_quota_error(exc):
                raise _build_quota_error(exc) from exc
            raise

    async def complete_with_image(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        image_mime: str = "image/png",
        response_schema: Any | None = None,
    ) -> tuple[str, UsageStats]:
        """Send prompt with image to Gemini multimodal endpoint.

        Args:
            response_schema: Optional google.genai.types.Schema instance.
                When provided, enforces structured JSON output via
                response_mime_type='application/json'. Used by placement
                mode when grid overlay is enabled.
        """
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=image_mime,
        )
        text_part = types.Part.from_text(text=user_prompt)

        config_kwargs: dict[str, Any] = {
            "system_instruction": system_prompt,
            "automatic_function_calling": _AFC_CONFIG,
        }
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[image_part, text_part],
                config=types.GenerateContentConfig(**config_kwargs),
            )
            return response.text or "", _extract_usage(response, self._model)
        except Exception as exc:
            if _is_quota_error(exc):
                raise _build_quota_error(exc) from exc
            raise


def _is_quota_error(exc: Exception) -> bool:
    """Return True if exception is a 429 quota/rate-limit error."""
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg


def _build_quota_error(exc: Exception) -> Exception:
    """Convert a raw 429 into a readable error with retry wait time."""
    retry_seconds = _parse_retry_seconds(exc)
    if retry_seconds is not None:
        wait = int(retry_seconds) + 1
        msg = f"API quota exceeded — retry in {wait}s. Check https://ai.dev/rate-limit for your model's quota."
    else:
        msg = "API quota exceeded — check your Gemini plan at https://ai.dev/rate-limit"
    logger.warning("Gemini 429: %s", msg)
    return RuntimeError(msg)


def _extract_usage(response: Any, model: str) -> UsageStats:
    """Extract token counts from a Gemini GenerateContentResponse.

    Gemini returns usage_metadata.prompt_token_count and
    candidates[0].token_count (output). Falls back to zeros if absent.
    """
    try:
        meta = getattr(response, "usage_metadata", None)
        input_tokens = int(getattr(meta, "prompt_token_count", 0) or 0)
        output_tokens = int(getattr(meta, "candidates_token_count", 0) or 0)
    except Exception:  # noqa: BLE001
        input_tokens = 0
        output_tokens = 0

    cost = estimate_cost(model, input_tokens, output_tokens)
    usage = UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
    )
    logger.debug(
        "Gemini usage: in=%d out=%d cost=%s",
        input_tokens, output_tokens,
        f"${cost:.6f}" if cost is not None else "unknown",
    )
    return usage


def fetch_available_models(
    api_key: str,
    on_done: Callable[[list[str]], None],
    on_error: Callable[[str], None],
) -> None:
    """Fetch generative models from Gemini API in a background thread.

    Calls on_done(model_list) or on_error(message) on the calling thread.
    Caller is responsible for marshalling back to the UI thread if needed.
    Filters to models that support generateContent and contain 'gemini'.
    Sorts flash models first (cheaper), then pro models.
    """
    import threading

    def _fetch() -> None:
        try:
            client = genai.Client(api_key=api_key)
            models = list(client.models.list())
            names: list[str] = []
            for m in models:
                name = m.name or ""
                if name.startswith("models/"):
                    name = name[len("models/"):]
                if "gemini" not in name.lower():
                    continue
                # log every candidate so we can see what the API returns
                supported = getattr(m, "supported_actions", None) or []
                logger.debug(
                    "Model candidate: %s | supported_actions=%s",
                    name, supported,
                )
                # only filter out if supported_actions is explicitly set
                # AND does not include generateContent — avoids dropping
                # models where the SDK returns an empty or missing list
                if supported and "generateContent" not in supported:
                    logger.debug("Skipping %s (no generateContent)", name)
                    continue
                names.append(name)

            flash = sorted(n for n in names if "flash" in n.lower())
            pro = sorted(n for n in names if "flash" not in n.lower())
            result = flash + pro

            logger.info(
                "Fetched %d Gemini models (%d total returned by API): %s",
                len(result), len(models), ", ".join(result),
            )
            if not result:
                result = _FALLBACK_MODELS
            on_done(result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch model list: %s", exc)
            on_error(str(exc))

    threading.Thread(target=_fetch, daemon=True).start()
