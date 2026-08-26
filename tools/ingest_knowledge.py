"""tools/ingest_knowledge.py — RAG knowledge base ingestion CLI.

Chunks markdown/text source files, embeds them with sentence-transformers,
and persists a Chroma collection to game_packs/<game_id>/rag/.

Run once per game pack (or when knowledge sources change). Output is committed
to the repo and loaded at runtime by ChromaRagService without re-embedding.

Usage
-----
    # Full build (reset any existing collection):
    uv run python tools/ingest_knowledge.py \
        --game-id timberborn \
        --source-dir game_packs/timberborn/knowledge \
        --game-version 0.6 \
        --reset

    # Incremental (skip already-ingested source files):
    uv run python tools/ingest_knowledge.py \
        --game-id timberborn \
        --source-dir game_packs/timberborn/knowledge

    # Custom embedding model (must match ChromaRagService at runtime):
    uv run python tools/ingest_knowledge.py \
        --game-id timberborn \
        --source-dir game_packs/timberborn/knowledge \
        --model paraphrase-MiniLM-L6-v2

Requires the [rag] optional dep group:
    uv sync --extra rag

Collection name convention: <game_id>_knowledge
Output path convention:     game_packs/<game_id>/rag/
"""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────

_DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_DEFAULT_CHUNK_SIZE_TOKENS = 400
_DEFAULT_CHUNK_OVERLAP_TOKENS = 50
_WORDS_PER_TOKEN_APPROX = 0.75
_SUPPORTED_EXTENSIONS = {".md", ".txt"}

_DEFAULT_CHUNK_SIZE_WORDS = int(_DEFAULT_CHUNK_SIZE_TOKENS * _WORDS_PER_TOKEN_APPROX)
_DEFAULT_CHUNK_OVERLAP_WORDS = int(_DEFAULT_CHUNK_OVERLAP_TOKENS * _WORDS_PER_TOKEN_APPROX)


# ── chunking ─────────────────────────────────────────────────────────────────

def _chunk_text(
    text: str,
    chunk_size_words: int,
    overlap_words: int,
) -> list[str]:
    """Split text into overlapping chunks by paragraph, respecting word limits."""
    _normalised = "\n\n".join(
        p.strip()
        for p in text.replace("\r\n", "\n").split("\n\n")
        if p.strip()
    )
    _paragraphs = _normalised.split("\n\n")

    _chunks: list[str] = []
    _current_words: list[str] = []

    def _flush() -> None:
        _text = " ".join(_current_words).strip()
        if _text:
            _chunks.append(_text)

    for _paragraph in _paragraphs:
        _para_words = _paragraph.split()

        # paragraph itself exceeds chunk size — sub-split by sentence
        if len(_para_words) > chunk_size_words:
            _sentences = _paragraph.replace("\n", " ").split(". ")
            for _sentence in _sentences:
                _sentence = _sentence.strip()
                if not _sentence:
                    continue
                _sent_words = _sentence.split()
                if len(_current_words) + len(_sent_words) > chunk_size_words:
                    _flush()
                    _current_words = _current_words[-overlap_words:] if overlap_words else []
                _current_words.extend(_sent_words)
            continue

        if len(_current_words) + len(_para_words) > chunk_size_words:
            _flush()
            _current_words = _current_words[-overlap_words:] if overlap_words else []

        _current_words.extend(_para_words)

    _flush()
    return [c for c in _chunks if c]


# ── ingestion ─────────────────────────────────────────────────────────────────

def _collect_source_files(source_dir: Path) -> list[Path]:
    _files: list[Path] = []
    for _ext in _SUPPORTED_EXTENSIONS:
        _files.extend(sorted(source_dir.rglob(f"*{_ext}")))
    return _files


def _already_ingested_sources(collection) -> set[str]:
    try:
        _result = collection.get(include=["metadatas"])
        return {
            m.get("source_file", "")
            for m in (_result.get("metadatas") or [])
            if m.get("source_file")
        }
    except Exception:  # noqa: BLE001
        return set()


def _safe_version_float(version: str) -> float:
    """Convert a version string to float for Chroma numeric metadata storage.

    Chroma's $gte operator requires int or float — string comparisons are
    not supported. '0.6' -> 0.6, '1.0' -> 1.0, 'any' -> 0.0 (no filtering).
    """
    try:
        return float(version)
    except (ValueError, TypeError):
        return 0.0


def ingest(
    game_id: str,
    source_dir: Path,
    game_packs_root: Path,
    game_version: str = "any",
    embedding_model: str = _DEFAULT_EMBEDDING_MODEL,
    chunk_size_words: int = _DEFAULT_CHUNK_SIZE_WORDS,
    overlap_words: int = _DEFAULT_CHUNK_OVERLAP_WORDS,
    reset: bool = False,
) -> int:
    """Ingest source documents into a Chroma collection."""
    try:
        import chromadb  # type: ignore[import-untyped]
        from chromadb.utils import embedding_functions  # type: ignore[import-untyped]
    except ImportError:
        logger.error("chromadb not installed. Install with: uv sync --extra rag")
        sys.exit(1)

    _collection_name = f"{game_id}_knowledge"
    _rag_dir = game_packs_root / game_id / "rag"
    _rag_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Embedding model : ONNXMiniLM_L6_V2 (chromadb built-in, no PyTorch)")
    logger.info("Collection      : %s", _collection_name)
    logger.info("Output path     : %s", _rag_dir)
    logger.info("Source dir      : %s", source_dir)
    logger.info("Game version    : %s", game_version)

    # ONNXMiniLM_L6_V2: chromadb built-in ONNX embedding, no PyTorch needed.
    # onnxruntime already present via rapidocr-onnxruntime (AD-06).
    _embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()
    _client = chromadb.PersistentClient(path=str(_rag_dir))

    if reset:
        try:
            _client.delete_collection(_collection_name)
            logger.info("Existing collection deleted (--reset)")
        except Exception:  # noqa: BLE001
            pass

    _collection = _client.get_or_create_collection(
        name=_collection_name,
        embedding_function=_embedding_fn,
    )
    logger.info("Collection ready: %d chunks already stored", _collection.count())

    _source_files = _collect_source_files(source_dir)
    if not _source_files:
        logger.warning("No .md or .txt files found under %s", source_dir)
        return 0

    _already_done = set() if reset else _already_ingested_sources(_collection)
    _total_chunks_added = 0

    for _source_path in _source_files:
        _rel_path = str(_source_path.relative_to(source_dir))

        if _rel_path in _already_done:
            logger.info("Skipping (already ingested): %s", _rel_path)
            continue

        _text = _source_path.read_text(encoding="utf-8")
        _chunks = _chunk_text(_text, chunk_size_words, overlap_words)

        if not _chunks:
            logger.warning("No chunks produced from %s — file may be empty", _rel_path)
            continue

        _ids = [f"{_rel_path}::chunk_{i}" for i in range(len(_chunks))]
        _metadatas = [
            {
                "source_file": _rel_path,
                "chunk_index": i,
                # game_version stored as float for Chroma $gte numeric comparison.
                # Falls back to 0.0 if version string is not numeric (e.g. "any").
                "game_version": _safe_version_float(game_version),
            }
            for i in range(len(_chunks))
        ]

        _collection.add(ids=_ids, documents=_chunks, metadatas=_metadatas)
        logger.info("Ingested: %s -> %d chunks", _rel_path, len(_chunks))
        _total_chunks_added += len(_chunks)

    logger.info(
        "Done. Added %d chunks. Collection total: %d chunks.",
        _total_chunks_added,
        _collection.count(),
    )
    return _total_chunks_added


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    _parser = argparse.ArgumentParser(
        prog="ingest_knowledge",
        description=textwrap.dedent("""\
            Chunk, embed, and persist game knowledge for GASSI RAG retrieval.
            Reads .md and .txt files from SOURCE_DIR and writes a Chroma
            persistent collection to game_packs/<game_id>/rag/.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _parser.add_argument("--game-id", required=True, metavar="GAME_ID")
    _parser.add_argument("--source-dir", required=True, metavar="DIR", type=Path)
    _parser.add_argument("--game-version", default="any", metavar="VERSION")
    _parser.add_argument("--model", default=_DEFAULT_EMBEDDING_MODEL, metavar="MODEL")
    _parser.add_argument(
        "--chunk-size", type=int, default=_DEFAULT_CHUNK_SIZE_TOKENS, metavar="TOKENS"
    )
    _parser.add_argument(
        "--chunk-overlap", type=int, default=_DEFAULT_CHUNK_OVERLAP_TOKENS, metavar="TOKENS"
    )
    _parser.add_argument("--reset", action="store_true")
    _parser.add_argument("--game-packs-root", default=None, metavar="DIR", type=Path)
    return _parser


def main() -> None:
    _parser = _build_arg_parser()
    _args = _parser.parse_args()

    _script_dir = Path(__file__).resolve().parent
    _repo_root = _script_dir.parent
    _game_packs_root: Path = _args.game_packs_root or (_repo_root / "game_packs")

    if not _game_packs_root.exists():
        logger.error("game_packs/ root not found: %s", _game_packs_root)
        sys.exit(1)

    if not (_game_packs_root / _args.game_id).exists():
        logger.error("Game pack '%s' not found under %s", _args.game_id, _game_packs_root)
        sys.exit(1)

    _source_dir: Path = _args.source_dir
    if not _source_dir.is_absolute():
        _source_dir = Path.cwd() / _source_dir
    if not _source_dir.exists():
        logger.error("Source dir not found: %s", _source_dir)
        sys.exit(1)

    _chunk_size_words = int(_args.chunk_size * _WORDS_PER_TOKEN_APPROX)
    _overlap_words = int(_args.chunk_overlap * _WORDS_PER_TOKEN_APPROX)

    ingest(
        game_id=_args.game_id,
        source_dir=_source_dir,
        game_packs_root=_game_packs_root,
        game_version=_args.game_version,
        embedding_model=_args.model,
        chunk_size_words=_chunk_size_words,
        overlap_words=_overlap_words,
        reset=_args.reset,
    )


if __name__ == "__main__":
    main()
