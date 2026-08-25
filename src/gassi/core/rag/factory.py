"""RagServiceFactory -- selects the correct RagService implementation.

Decision logic:
1. Is collection_name provided in manifest?      No  -> NullRagService
2. Does game_packs/<game_id>/rag/ folder exist?  No  -> NullRagService
3. Is chromadb importable?                       No  -> NullRagService (warn)
4. All checks pass                                   -> ChromaRagService

This keeps the factory as the single place that knows about both implementations.
ViewModel and callers only ever see the RagService Protocol.
"""

from __future__ import annotations

import logging
from pathlib import Path

from gassi.core.rag.null_backend import NullRagService
from gassi.core.rag.protocol import RagService

logger = logging.getLogger(__name__)


class RagServiceFactory:
    """Static factory -- no instantiation needed."""

    @staticmethod
    def for_game_pack(
        game_pack_path: Path,
        collection_name: str | None = None,
    ) -> RagService:
        """Return the appropriate RagService for the given game pack.

        Args:
            game_pack_path:     Absolute path to the game pack folder
                                (e.g. game_packs/timberborn/).
            collection_name:    Chroma collection name from manifest
                                (rag_collection_name field). When None,
                                returns NullRagService.

        Returns:
            ChromaRagService if all prerequisites met, else NullRagService.
        """
        _rag_dir = game_pack_path / "rag"

        if not collection_name:
            logger.debug(
                "RAG disabled for '%s' -- no collection_name in manifest",
                game_pack_path.name,
            )
            return NullRagService()

        if not _rag_dir.exists():
            logger.debug(
                "RAG disabled for '%s' -- no rag/ folder at %s",
                game_pack_path.name,
                _rag_dir,
            )
            return NullRagService()

        try:
            from gassi.core.rag.chroma_backend import ChromaRagService  # noqa: PLC0415
            _service = ChromaRagService(
                collection_path=_rag_dir,
                collection_name=collection_name,
            )
            if _service.is_available():
                return _service

            logger.warning(
                "RAG collection '%s' could not be loaded -- falling back to NullRagService",
                collection_name,
            )
            return NullRagService()

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ChromaRagService init failed for '%s': %s -- using NullRagService",
                collection_name,
                exc,
            )
            return NullRagService()
