"""Embedding generation and storage using Voyage AI via langchain-anthropic."""

from __future__ import annotations

import uuid
from typing import Any

from langchain_anthropic import AnthropicEmbeddings

from src.config import settings
from src.db.connection import execute_command
from src.ingestion.splitter import TextChunk


def build_embeddings_model() -> AnthropicEmbeddings:
    """Build the Voyage AI embeddings model through the Anthropic provider.

    Returns:
        Configured AnthropicEmbeddings instance for voyage-large-2.
    """
    return AnthropicEmbeddings(
        model=settings.embedding_model,
        anthropic_api_key=settings.anthropic_api_key,
    )


async def embed_chunks(
    chunks: list[TextChunk],
    document_id: uuid.UUID,
    embeddings_model: AnthropicEmbeddings | None = None,
) -> list[uuid.UUID]:
    """Generate embeddings for chunks and persist them to the database.

    Each chunk is first stored in the chunks table, then its embedding
    vector is stored in the embeddings table with a reference to the chunk.

    Args:
        chunks: List of text chunks to embed.
        document_id: UUID of the parent document.
        embeddings_model: Optional pre-built embeddings model; built fresh if None.

    Returns:
        List of chunk UUIDs that were stored.
    """
    if embeddings_model is None:
        embeddings_model = build_embeddings_model()

    texts = [c.content for c in chunks]
    vectors: list[list[float]] = embeddings_model.embed_documents(texts)

    chunk_ids: list[uuid.UUID] = []

    for chunk, vector in zip(chunks, vectors):
        chunk_id = uuid.uuid4()
        chunk_ids.append(chunk_id)

        await execute_command(
            """
            INSERT INTO chunks (id, document_id, content, page_number, chunk_index, metadata)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            chunk_id,
            document_id,
            chunk.content,
            chunk.page_number,
            chunk.chunk_index,
            '{"source": "pdf"}',
        )

        await execute_command(
            """
            INSERT INTO embeddings (id, chunk_id, embedding, model)
            VALUES ($1, $2, $3::vector, $4)
            """,
            uuid.uuid4(),
            chunk_id,
            str(vector),
            settings.embedding_model,
        )

    return chunk_ids


def embed_query(query: str, embeddings_model: AnthropicEmbeddings | None = None) -> list[float]:
    """Generate an embedding vector for a query string.

    Args:
        query: The question or search text to embed.
        embeddings_model: Optional pre-built model; created fresh if None.

    Returns:
        Float list representing the query embedding vector.
    """
    if embeddings_model is None:
        embeddings_model = build_embeddings_model()
    return embeddings_model.embed_query(query)


def compute_embedding_cost(num_tokens: int) -> dict[str, Any]:
    """Estimate the cost of generating embeddings.

    Args:
        num_tokens: Approximate total token count.

    Returns:
        Dict with model name, token count, and estimated USD cost.
    """
    # Voyage AI pricing: $0.12 per 1M tokens for voyage-large-2
    cost_per_million = 0.12
    cost = (num_tokens / 1_000_000) * cost_per_million
    return {
        "model": settings.embedding_model,
        "tokens": num_tokens,
        "cost_usd": round(cost, 6),
    }
