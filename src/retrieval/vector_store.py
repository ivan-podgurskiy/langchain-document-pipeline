"""pgvector-based HNSW vector store for semantic chunk retrieval."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from src.config import settings
from src.db.connection import execute_query
from src.ingestion.embedder import embed_query


@dataclass
class SearchResult:
    """A single result from semantic similarity search."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    page_number: int
    similarity_score: float
    metadata: dict


async def similarity_search(
    query: str,
    top_k: int | None = None,
    threshold: float | None = None,
    document_id: uuid.UUID | None = None,
) -> list[SearchResult]:
    """Perform HNSW cosine similarity search over stored embeddings.

    Queries the pgvector HNSW index using cosine distance.  Results are
    optionally filtered by document and by a minimum similarity threshold.

    Args:
        query: Natural language question or search phrase.
        top_k: Maximum number of results to return.  Defaults to settings value.
        threshold: Minimum cosine similarity (0–1).  Defaults to settings value.
        document_id: Optional UUID to restrict search to one document.

    Returns:
        Ranked list of SearchResult objects, highest similarity first.
    """
    k = top_k or settings.vector_top_k
    min_score = threshold if threshold is not None else settings.vector_similarity_threshold

    query_vector = embed_query(query)
    vector_str = str(query_vector)

    if document_id is not None:
        rows = await execute_query(
            """
            SELECT
                c.id            AS chunk_id,
                c.document_id,
                c.content,
                c.page_number,
                c.metadata,
                1 - (e.embedding <=> $1::vector) AS similarity
            FROM embeddings e
            JOIN chunks c ON c.id = e.chunk_id
            WHERE c.document_id = $2
              AND 1 - (e.embedding <=> $1::vector) >= $3
            ORDER BY e.embedding <=> $1::vector
            LIMIT $4
            """,
            vector_str,
            document_id,
            min_score,
            k,
        )
    else:
        rows = await execute_query(
            """
            SELECT
                c.id            AS chunk_id,
                c.document_id,
                c.content,
                c.page_number,
                c.metadata,
                1 - (e.embedding <=> $1::vector) AS similarity
            FROM embeddings e
            JOIN chunks c ON c.id = e.chunk_id
            WHERE 1 - (e.embedding <=> $1::vector) >= $2
            ORDER BY e.embedding <=> $1::vector
            LIMIT $3
            """,
            vector_str,
            min_score,
            k,
        )

    return [
        SearchResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            content=row["content"],
            page_number=row["page_number"],
            similarity_score=float(row["similarity"]),
            metadata=json.loads(row["metadata"])
            if isinstance(row["metadata"], str)
            else (row["metadata"] or {}),
        )
        for row in rows
    ]


async def get_chunk_by_id(chunk_id: uuid.UUID) -> SearchResult | None:
    """Retrieve a single chunk by its UUID.

    Args:
        chunk_id: UUID of the chunk to retrieve.

    Returns:
        SearchResult if found, None otherwise.
    """
    rows = await execute_query(
        """
        SELECT c.id AS chunk_id, c.document_id, c.content, c.page_number, c.metadata
        FROM chunks c
        WHERE c.id = $1
        """,
        chunk_id,
    )
    if not rows:
        return None
    row = rows[0]
    return SearchResult(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        content=row["content"],
        page_number=row["page_number"],
        similarity_score=1.0,
        metadata=json.loads(row["metadata"])
        if isinstance(row["metadata"], str)
        else (row["metadata"] or {}),
    )
