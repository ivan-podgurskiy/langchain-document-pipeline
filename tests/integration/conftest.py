"""Fixtures and helpers for PostgreSQL integration tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.db.connection import close_pool, execute_command, get_pool


async def _truncate_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE embeddings, chunks, documents CASCADE")


async def insert_test_document(
    *,
    filename: str = "prior_auth.pdf",
    pages: list[str] | None = None,
    embedding: list[float] | None = None,
) -> uuid.UUID:
    """Insert a done document with optional chunk embeddings for search tests."""
    doc_id = uuid.uuid4()
    page_texts = pages or ["Patient requires E1390 oxygen concentrator for COPD."]
    await execute_command(
        """
        INSERT INTO documents (id, filename, file_hash, page_count, status)
        VALUES ($1, $2, $3, $4, 'done')
        """,
        doc_id,
        filename,
        str(uuid.uuid4()),
        len(page_texts),
    )

    for page_number, content in enumerate(page_texts, start=1):
        chunk_id = uuid.uuid4()
        await execute_command(
            """
            INSERT INTO chunks (id, document_id, content, page_number, chunk_index)
            VALUES ($1, $2, $3, $4, 0)
            """,
            chunk_id,
            doc_id,
            content,
            page_number,
        )
        if embedding is not None:
            await execute_command(
                """
                INSERT INTO embeddings (chunk_id, embedding, model)
                VALUES ($1, $2::vector, 'test-model')
                """,
                chunk_id,
                str(embedding),
            )

    return doc_id


@pytest.fixture
async def db_session() -> AsyncIterator[None]:
    """Reset pool, ensure schema objects exist, and truncate tables per test."""
    import src.db.connection as db_connection

    await close_pool()
    db_connection._pool = None

    await _truncate_tables()

    yield

    await close_pool()
    db_connection._pool = None


@pytest.fixture
async def integration_client(db_session: None) -> AsyncIterator[AsyncClient]:
    """HTTP client with FastAPI lifespan against a live PostgreSQL database."""
    from src.main import app

    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
