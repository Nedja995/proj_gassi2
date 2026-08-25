"""NullRagService -- no-op RagService used when no Chroma collection is present.

Returned by RagServiceFactory when the game pack has no rag/ folder or
when chromadb is not installed.

Deliberately imports nothing from chromadb so that the optional [rag] dep
group is truly optional -- the app starts and runs normally without it.
"""


class NullRagService:
    """RagService implementation that always returns an empty result set.

    Satisfies the RagService Protocol structurally (no ABC inheritance needed).
    ViewModel code should always call is_available() before formatting a
    RAG context block to avoid emitting an empty ## Retrieved Knowledge section.
    """

    def query(
        self,
        text: str,
        top_k: int = 3,
        min_game_version: str | None = None,
    ) -> list[str]:
        """Return empty list -- no collection available."""
        return []

    def is_available(self) -> bool:
        """Always False -- no backing collection."""
        return False
