from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from backend.agents.state import ParsedFile
from backend.config import get_settings
from backend.core.logging import get_logger
from backend.database.qdrant import upsert_points

logger = get_logger(__name__)

_model: SentenceTransformer | None = None

# Max characters per embedding chunk (model context limit)
_MAX_CHUNK_CHARS = 2000


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


def _build_chunks_from_file(pf: ParsedFile) -> list[dict[str, Any]]:
    """
    Build semantic chunks from a parsed file.
    Chunks are based on AST symbols, not naive line splits.
    Each symbol becomes one chunk with its surrounding context.

    Uses the full file source (read from disk path) when available so that
    symbols beyond the raw_snippet 400-line cap still get correct code.
    """
    chunks: list[dict[str, Any]] = []

    # Prefer reading the file from disk so we aren't limited to raw_snippet
    # (raw_snippet is capped at SNIPPET_LINES for LLM context, not embeddings)
    full_source_lines: list[str] | None = None
    file_path = pf.get("path")
    if file_path:
        try:
            full_source_lines = Path(file_path).read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except Exception:
            pass  # Fall back to raw_snippet

    snippet_lines = pf["raw_snippet"].splitlines()
    # Use whichever source is longer
    lines = full_source_lines if full_source_lines is not None else snippet_lines

    if not pf["symbols"]:
        # Fall back to whole-file snippet for files with no symbols
        if pf["raw_snippet"].strip():
            chunks.append({
                "text": pf["raw_snippet"][:_MAX_CHUNK_CHARS],
                "metadata": {
                    "file_path": pf["path"],
                    "language": pf["language"],
                    "chunk_type": "file_snippet",
                },
            })
        return chunks

    for sym in pf["symbols"]:
        start = max(0, sym["start_line"] - 1)
        end = min(len(lines), sym["end_line"])

        # Guard: if symbol lines are beyond what we have, skip
        if start >= len(lines):
            continue

        symbol_code = "\n".join(lines[start:end])
        if not symbol_code.strip():
            continue

        if sym.get("docstring"):
            text = f"# {sym['kind']}: {sym['name']}\n# {sym['docstring']}\n{symbol_code}"
        else:
            text = f"# {sym['kind']}: {sym['name']}\n{symbol_code}"

        chunks.append({
            "text": text[:_MAX_CHUNK_CHARS],
            "metadata": {
                "file_path": pf["path"],
                "language": pf["language"],
                "symbol_name": sym["name"],
                "symbol_kind": sym["kind"],
                "start_line": sym["start_line"],
                "end_line": sym["end_line"],
                "chunk_type": "symbol",
            },
        })

    return chunks


async def embed_and_store(repo_id: str, parsed_files: list[ParsedFile]) -> int:
    """Embed all AST-based chunks and store in Qdrant. Returns number of stored points."""
    all_chunks: list[dict[str, Any]] = []
    for pf in parsed_files:
        all_chunks.extend(_build_chunks_from_file(pf))

    if not all_chunks:
        return 0

    texts = [c["text"] for c in all_chunks]
    logger.info("embedding_start", repo_id=repo_id, chunks=len(texts))

    batch_size = 64
    points: list[PointStruct] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vectors = embed_texts(batch)
        for j, vector in enumerate(vectors):
            chunk = all_chunks[i + j]
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "repo_id": repo_id,
                    **chunk["metadata"],
                    "text": chunk["text"][:500],
                },
            ))

    await upsert_points(points)
    logger.info("embedding_complete", repo_id=repo_id, stored=len(points))
    return len(points)


async def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
