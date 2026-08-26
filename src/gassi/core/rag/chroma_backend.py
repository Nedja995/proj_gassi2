"""ChromaRagService -- Chroma persistent vector DB backend for game knowledge retrieval.

Requires the optional [rag] dependency group:
    uv sync --extra rag

Uses chromadb's built-in ONNXMiniLM_L6_V2 embedding function -- no PyTorch or
sentence-transformers needed. onnxruntime is already present via rapidocr-onnxruntime.

Loads a pre-ingested Chroma collection from game_packs/<game_id>/rag/.
Collections are created by tools/ingest_knowledge.py (v0.6.2) and committed
to the repo -- no runtime ingestion happens here.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ChromaRagService:
    """RagService backed by a persistent Chroma collection.

    Satisfies the RagService Protocol structurally.

    Args:
        collection_path:    Absolute path to the Chroma persistent directory
                            (i.e. game_packs/<game_id>/rag/).
        collection_name:    Chroma collection name inside that directory.
                            Conventionally <game_id>_knowledge.
    """

    def __init__(
        self,
        collection_path: Path,
        collection_name: str,
    ) -> None:
        self._collection_path = collection_path
        self._collection_name = collection_name
        self._collection = None  # loaded lazily on first query

        self._load_collection()

    def _load_collection(self) -> None:
        """Load the Chroma persistent client and collection.

        Uses chromadb's built-in ONNXMiniLM_L6_V2 -- no PyTorch needed.
        Deferred import keeps chromadb out of the import graph when the
        optional dep group is not installed. Errors are caught and logged --
        the service gracefully degrades to unavailable rather than crashing.
        """
        try:
            import chromadb  # type: ignore[import-untyped]
            from chromadb.utils import embedding_functions  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "chromadb not installed -- RAG unavailable. "
                "Install with: uv sync --extra rag"
            )
            return

        try:
            # ONNXMiniLM_L6_V2: chromadb built-in, uses onnxruntime (already
            # installed via rapidocr-onnxruntime). No PyTorch dependency (AD-06).
            _embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()
            _client = chromadb.PersistentClient(path=str(self._collection_path))
            self._collection = _client.get_collection(
                name=self._collection_name,
                embedding_function=_embedding_fn,
            )
            logger.info(
                "RAG collection loaded: '%s' (%d chunks) from %s",
                self._collection_name,
                self._collection.count(),
                self._collection_path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to load RAG collection '%s' from %s: %s",
                self._collection_name,
                self._collection_path,
                exc,
            )
            self._collection = None

    def query(
        self,
        text: str,
        top_k: int = 3,
        min_game_version: str | None = None,
    ) -> list[str]:
        """Query the collection for the top-k most relevant chunks.

        Args:
            text:               Query string to embed and search against.
            top_k:              Maximum number of results to return.
            min_game_version:   When set, applies a Chroma where filter to
                                exclude chunks with game_version < this value.

        Returns:
            List of document strings, most relevant first. Empty on any error.
        """
        if self._collection is None:
            return []

        if not text or not text.strip():
            return []

        _where_filter: dict | None = None
        if min_game_version:
            try:
                _version_float = float(min_game_version)
                _where_filter = {"game_version": {"$gte": _version_float}}
            except (ValueError, TypeError):
                logger.warning(
                    "RAG: could not convert min_game_version '%s' to float — "
                    "version filter skipped",
                    min_game_version,
                )

        try:
            _query_kwargs: dict = {
                "query_texts": [text],
                "n_results": min(top_k, self._collection.count()),
                "include": ["documents"],
            }
            if _where_filter:
                _query_kwargs["where"] = _where_filter

            _results = self._collection.query(**_query_kwargs)
            _documents: list[list[str]] = _results.get("documents", [[]])
            return _documents[0] if _documents else []

        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG query failed: %s", exc)
            return []

    def is_available(self) -> bool:
        """Return True if the collection was loaded successfully."""
        return self._collection is not None
