"""Gemini AI backend implementation.

Handles 429 RESOURCE_EXHAUSTED by reading the retryDelay from the
error response and surfacing a human-readable message with the wait time.
AFC is explicitly disabled since GASSI does not use function calling tools.
"""

import logging
import re
from collections.abc import Callable

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# suppress AFC warning — we never use function calling tools
_AFC_CONFIG = types.AutomaticFunctionCallingConfig(disable=True)

_RETRY_DELAY_RE = re.compile(r"retry[^\d]*(\d+(?:\.\d+)?)\s*s", re.IGNORECASE)

# models shown in dropdown when API fetch fails
_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-3.6-flash",
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

    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
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
            return response.text or ""
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
    ) -> str:
        """Send prompt with image to Gemini multimodal endpoint."""
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=image_mime,
        )
        text_part = types.Part.from_text(text=user_prompt)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[image_part, text_part],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    automatic_function_calling=_AFC_CONFIG,
                ),
            )
            return response.text or ""
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
        msg = f"API quota exceeded — retry in {wait}s (free tier: 20 req/day on gemini-3.6-flash)"
    else:
        msg = "API quota exceeded — check your Gemini plan at https://ai.dev/rate-limit"
    logger.warning("Gemini 429: %s", msg)
    return RuntimeError(msg)


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
            models = client.models.list()
            names: list[str] = []
            for m in models:
                name = m.name or ""
                # strip "models/" prefix if present
                if name.startswith("models/"):
                    name = name[len("models/"):]
                # only generative gemini models
                if "gemini" not in name.lower():
                    continue
                supported = getattr(m, "supported_actions", None) or []
                if supported and "generateContent" not in supported:
                    continue
                names.append(name)

            # sort: flash first, then pro, alphabetical within each group
            flash = sorted(n for n in names if "flash" in n.lower())
            pro = sorted(n for n in names if "flash" not in n.lower())
            result = flash + pro

            if not result:
                result = _FALLBACK_MODELS
            logger.info("Fetched %d Gemini models", len(result))
            on_done(result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch model list: %s", exc)
            on_error(str(exc))

    threading.Thread(target=_fetch, daemon=True).start()
