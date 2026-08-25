"""RAG (Retrieval-Augmented Generation) subsystem.

Provides game-specific knowledge retrieval to augment AI prompts with
formula-level, wiki-sourced, and patch-note content without bloating
the static system prompt.

Public API:
    RagService          -- Protocol (typing.Protocol, structural subtyping)
    NullRagService      -- no-op fallback when no collection is present
    ChromaRagService    -- persistent Chroma vector DB backend
    RagServiceFactory   -- selects correct implementation per game pack path
"""

from gassi.core.rag.protocol import RagService
from gassi.core.rag.null_backend import NullRagService
from gassi.core.rag.factory import RagServiceFactory

__all__ = [
    "RagService",
    "NullRagService",
    "RagServiceFactory",
]
