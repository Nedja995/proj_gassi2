"""Application enumerations."""

from enum import Enum


class AssistantMode(Enum):
    """Top-level operating mode of the assistant."""

    IDLE = "idle"
    ADVISOR = "advisor"        # periodic polling — OCR or screenshot
    PLACEMENT = "placement"    # on-demand — full window screenshot + user prompt


class AdvisorInputSource(Enum):
    """Input method for Advisor mode."""

    OCR = "ocr"                # local RapidOCR -> text -> Gemini
    SCREENSHOT = "screenshot"  # cropped hud_region image -> Gemini directly


class AiProvider(Enum):
    """AI backend provider selection.

    Stored in settings.json as a string value.
    Settings always wins over any pack-level preferred_backend hint.

    Provider tiers (v0.9.x):
      Cloud paid:  GEMINI, CLAUDE
      Cloud free:  GROQ, TOGETHER, HUGGINGFACE
      Local:       OLLAMA
    """

    GEMINI = "gemini"
    CLAUDE = "claude"
    # v0.9.x OpenAI-compatible providers (require [providers] extras)
    OLLAMA = "ollama"
    GROQ = "groq"
    TOGETHER = "together"
    HUGGINGFACE = "huggingface"  # Inference API (cloud) only — AD-06 blocks local transformers

    # Convenience sets — used by factory and Settings UI
    @classmethod
    def openai_compat_providers(cls) -> frozenset["AiProvider"]:
        """Providers backed by OpenAiCompatBackend (openai SDK, [providers] extras).

        HuggingFace here refers to the Inference API (cloud/serverless) only.
        Local HuggingFace via transformers library is blocked by AD-06 (no PyTorch).
        """
        return frozenset({cls.OLLAMA, cls.GROQ, cls.TOGETHER, cls.HUGGINGFACE})

    @classmethod
    def cloud_providers(cls) -> frozenset["AiProvider"]:
        """Providers that require an external API key."""
        return frozenset({cls.GEMINI, cls.CLAUDE, cls.GROQ, cls.TOGETHER, cls.HUGGINGFACE})

    @classmethod
    def local_providers(cls) -> frozenset["AiProvider"]:
        """Providers that run locally (no API key, no cloud)."""
        return frozenset({cls.OLLAMA})
