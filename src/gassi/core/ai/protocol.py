"""AI backend protocol — interface contract for all AI providers."""

from typing import Protocol


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
    ) -> str:
        """Send a prompt with an attached image and return the response text."""
        ...
