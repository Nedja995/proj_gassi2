"""Ollama local SLM backend (v0.9.3).

Runs against a local (or LAN) Ollama server via its OpenAI-compatible
/v1/chat/completions endpoint. No API key — Ollama ignores the Bearer
token, but the openai SDK requires a non-empty string ("ollama" used).

Requires the optional [providers] extras:
    uv sync --extra providers

Also requires a running Ollama server:
    https://ollama.com/download
    ollama pull moondream2          # primary vision model (~1.8GB VRAM)
    ollama pull llama3.2:3b         # text-only, low VRAM (~2GB)
    ollama pull qwen2.5vl:7b        # best quality vision (~6GB VRAM)

The server URL is configurable via AppSettings.ollama_base_url
(default http://localhost:11434). Point it at a remote server or Docker
container to use Ollama on another machine.

Model list:
    fetch_ollama_models() polls /api/tags on the Ollama server in a
    background thread and returns whatever models the user has pulled.
    Falls back to OLLAMA_RECOMMENDED_MODELS when the server is unreachable.

Vision path:
    Uses the standard OpenAI image_url content block from the base class.
    Requires a vision-capable model (moondream2, qwen2.5vl, llama3.2-vision).
    Text-only models (llama3.2:3b) will error on complete_with_image() —
    the Settings UI should surface this constraint via the model description.
"""

import logging
import threading
from collections.abc import Callable

from gassi.core.ai.openai_compat_backend import OpenAiCompatBackend

logger = logging.getLogger(__name__)

# Default Ollama server base URL (OpenAI-compat endpoint path included).
_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"

# Recommended models shown in Settings when the Ollama server is unreachable.
# Format: "model_name" — must match exact Ollama pull names.
# Ordered: best fit for GTX 1660 Super (6GB VRAM) first.
OLLAMA_RECOMMENDED_MODELS: list[str] = [
    "moondream2",        # 2B vision — ~1.8GB VRAM, fast, primary recommendation
    "llama3.2:3b",       # 3B text-only — ~2.0GB VRAM, OCR path only
    "qwen2.5vl:7b",      # 7B vision — ~6.1GB VRAM, best quality, tight fit
    "llama3.2-vision",   # 11B vision — RAM offload, slow on weak GPU
]

# VRAM annotation map — shown as hints in Settings model picker.
OLLAMA_MODEL_VRAM: dict[str, str] = {
    "moondream2":       "~1.8 GB VRAM — recommended for 6 GB cards",
    "llama3.2:3b":      "~2.0 GB VRAM — text-only (OCR path)",
    "qwen2.5vl:7b":     "~6.1 GB VRAM — best quality, tight fit on 6 GB",
    "llama3.2-vision":  "~11 GB — requires RAM offload on 6 GB cards (slow)",
}


class OllamaBackend(OpenAiCompatBackend):
    """Ollama local SLM backend.

    Connects to a running Ollama server via the OpenAI-compatible endpoint.
    No API key required — the server URL is the only required configuration.
    """

    _provider_name = "Ollama"
    # api_key is set per-instance in __init__ (not a class-level constant
    # because the base_url is runtime-configured).

    def __init__(self, base_url: str = _OLLAMA_DEFAULT_BASE_URL, model: str = "moondream2") -> None:
        """Initialise the Ollama backend.

        Args:
            base_url: Ollama server root URL (without /v1 path).
                      AppSettings.ollama_base_url feeds this at runtime.
            model:    Model name as it appears in `ollama list`.
                      AppSettings.ollama_model feeds this at runtime.
        """
        self._base_url = base_url.rstrip("/") + "/v1"
        self._api_key = "ollama"  # required non-empty string; Ollama ignores it
        self._model = model
        super().__init__()
        logger.info("OllamaBackend: model=%s server=%s", self._model, base_url)


def fetch_ollama_models(
    base_url: str,
    on_done: Callable[[list[str]], None],
    on_error: Callable[[str], None],
) -> None:
    """Fetch the list of locally pulled models from the Ollama server.

    Polls GET <base_url>/api/tags in a background daemon thread.
    Calls on_done(model_names) or on_error(message) when complete.
    Callers are responsible for marshalling back to the UI thread if needed.

    Falls back to OLLAMA_RECOMMENDED_MODELS when the server is unreachable
    so the Settings model picker is never empty.

    Args:
        base_url: Ollama server root URL (e.g. "http://localhost:11434").
        on_done:  Callback receiving list[str] of model name strings.
        on_error: Callback receiving an error message string.
    """
    def _fetch() -> None:
        import urllib.request  # noqa: PLC0415
        import json            # noqa: PLC0415

        tags_url = base_url.rstrip("/") + "/api/tags"
        try:
            with urllib.request.urlopen(tags_url, timeout=3) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode())
            models_raw = payload.get("models", [])
            model_names = [m.get("name", "") for m in models_raw if m.get("name")]
            if not model_names:
                logger.info("Ollama /api/tags returned empty model list — using recommendations")
                on_done(OLLAMA_RECOMMENDED_MODELS)
                return
            logger.info("Ollama models available: %s", ", ".join(model_names))
            on_done(model_names)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not reach Ollama server at %s: %s — showing recommended models",
                base_url, exc,
            )
            on_error(str(exc))

    threading.Thread(target=_fetch, daemon=True).start()
