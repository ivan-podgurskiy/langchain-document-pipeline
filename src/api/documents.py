"""Document listing and detail endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.connection import execute_query

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentListItem(BaseModel):
    """Brief document info for list view."""

    id: str
    filename: str
    page_count: int
    chunk_count: int
    status: str
    created_at: str


class ChunkItem(BaseModel):
    """Chunk info for document detail."""

    id: str
    page_number: int
    chunk_index: int
    content: str
    content_preview: str


class DocumentDetailResponse(BaseModel):
    """Full document details with chunks."""

    id: str
    filename: str
    file_hash: str
    page_count: int
    chunk_count: int
    status: str
    error_msg: Optional[str]
    created_at: str
    chunks: list[ChunkItem]


@router.get("/", response_model=list[DocumentListItem])
async def list_documents() -> list[DocumentListItem]:
    """List all ingested documents, newest first."""
    rows = await execute_query(
        """
        SELECT d.id, d.filename, d.page_count, d.status, d.created_at,
               (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count
        FROM documents d
        ORDER BY d.created_at DESC
        """
    )
    return [
        DocumentListItem(
            id=str(r["id"]),
            filename=r["filename"],
            page_count=r["page_count"],
            chunk_count=r["chunk_count"],
            status=r["status"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
        )
        for r in rows
    ]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: str) -> DocumentDetailResponse:
    """Get document details with all chunks."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")

    rows = await execute_query(
        """
        SELECT d.id, d.filename, d.file_hash, d.page_count, d.status, d.error_msg, d.created_at
        FROM documents d
        WHERE d.id = $1
        """,
        doc_uuid,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")

    r = rows[0]
    chunk_rows = await execute_query(
        """
        SELECT c.id, c.page_number, c.chunk_index, c.content
        FROM chunks c
        WHERE c.document_id = $1
        ORDER BY c.page_number, c.chunk_index
        """,
        doc_uuid,
    )

    chunk_count = len(chunk_rows)
    chunks = [
        ChunkItem(
            id=str(c["id"]),
            page_number=c["page_number"],
            chunk_index=c["chunk_index"],
            content=c["content"],
            content_preview=c["content"][:200] + ("..." if len(c["content"]) > 200 else ""),
        )
        for c in chunk_rows
    ]

    return DocumentDetailResponse(
        id=str(r["id"]),
        filename=r["filename"],
        file_hash=r["file_hash"],
        page_count=r["page_count"],
        chunk_count=chunk_count,
        status=r["status"],
        error_msg=r["error_msg"],
        created_at=r["created_at"].isoformat() if r["created_at"] else "",
        chunks=chunks,
    )
