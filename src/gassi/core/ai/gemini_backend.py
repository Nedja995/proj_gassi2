"""Gemini AI backend implementation."""

import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


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
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        return response.text or ""

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

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[image_part, text_part],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        return response.text or ""
