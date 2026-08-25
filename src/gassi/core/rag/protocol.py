"""RagService Protocol -- interface contract for all RAG backends.

Follows the same structural-subtyping pattern as AiBackend (AD-02).
Implementations: NullRagService (no-op), ChromaRagService (Chroma vector DB).
New backends slot in without touching ViewModel or factory call sites.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class RagService(Protocol):
    """Abstract interface for game knowledge retrieval.

    All implementations must be synchronous -- RAG queries run on the
    main thread before the async bridge submits the AI call, so there
    is no benefit to async here and it avoids bridging complexity.
    """

    def query(
        self,
        text: str,
        top_k: int = 3,
        min_game_version: str | None = None,
    ) -> list[str]:
        """Retrieve the top-k most relevant knowledge chunks for text.

        Args:
            text:               Query string (OCR text, placement prompt, etc.)
            top_k:              Maximum number of chunks to return.
            min_game_version:   When set, exclude chunks tagged to game versions
                                older than this string (via Chroma where filter).

        Returns:
            List of chunk strings, most relevant first.
            Empty list if no collection is available or query yields no results.
        """
        ...

    def is_available(self) -> bool:
        """Return True if a backing collection is loaded and queryable."""
        ...
