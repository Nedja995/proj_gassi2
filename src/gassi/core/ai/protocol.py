"""AI backend protocol — interface contract for all AI providers."""

from typing import Any, Protocol

from gassi.models.results import UsageStats


class AiBackend(Protocol):
    """Abstract interface for AI completion providers.

    Both methods return a tuple[str, UsageStats] — response text plus
    token usage/cost metadata. ViewModel unpacks and accumulates stats.

    v0.7.3: Protocol updated from bare str to tuple[str, UsageStats].
    All backends (GeminiBackend, ClaudeBackend) updated atomically.
    """

    async def complete_text(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, UsageStats]:
        """Send a text-only prompt and return (response_text, usage_stats)."""
        ...

    async def complete_with_image(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        image_mime: str = "image/png",
        response_schema: Any | None = None,
    ) -> tuple[str, UsageStats]:
        """Send a prompt with an attached image and return (response_text, usage_stats).

        Args:
            response_schema: Optional structured output schema (provider-specific).
                When provided, the backend enforces JSON output matching the schema.
                Used by placement mode when grid overlay is enabled.
        """
        ...
