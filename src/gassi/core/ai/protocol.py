"""AI backend protocol — interface contract for all AI providers."""

from typing import Any, Protocol


class AiBackend(Protocol):
    """Abstract interface for AI completion providers.

    v1: GeminiBackend only.
    Future: ClaudeBackend, OllamaBackend slot in without touching ViewModel.
    """

    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        """Send a text-only prompt and return the response text."""
        ...

    async def complete_with_image(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        image_mime: str = "image/png",
        response_schema: Any | None = None,
    ) -> str:
        """Send a prompt with an attached image and return the response text.

        Args:
            response_schema: Optional structured output schema (provider-specific).
                When provided, the backend enforces JSON output matching the schema.
                Used by placement mode when grid overlay is enabled.
        """
        ...
