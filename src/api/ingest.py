"""POST /ingest endpoint: upload PDF, chunk, embed, and store."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.config import settings
from src.db.connection import execute_command, execute_query
from src.ingestion.embedder import embed_chunks
from src.ingestion.pdf_loader import load_pdf_bytes
from src.ingestion.splitter import split_document

router = APIRouter(prefix="/ingest", tags=["ingestion"])

MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


class IngestResponse(BaseModel):
    """Response returned after successful document ingestion."""

    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    status: str


class IngestStatusResponse(BaseModel):
    """Response for ingestion status polling."""

    document_id: str
    filename: str
    status: str
    chunk_count: int


@router.post("/", response_model=IngestResponse)
async def ingest_document(
    file: Annotated[UploadFile, File(description="PDF file to ingest")],
) -> IngestResponse:
    """Upload and process a PDF document.

    Reads the uploaded PDF, splits it into chunks, generates embeddings
    via Voyage AI, and stores everything in PostgreSQL.

    Args:
        file: Uploaded PDF file (multipart/form-data).

    Returns:
        IngestResponse with the assigned document_id and chunk count.

    Raises:
        HTTPException 400: If the file is not a PDF or exceeds the size limit.
        HTTPException 409: If the document was already ingested (same file hash).
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB",
        )

    doc_content = load_pdf_bytes(content, file.filename)

    # Check for duplicate
    existing = await execute_query(
        "SELECT id FROM documents WHERE file_hash = $1",
        doc_content.file_hash,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Document already ingested (id={existing[0]['id']})",
        )

    doc_id = uuid.uuid4()
    await execute_command(
        """
        INSERT INTO documents (id, filename, file_hash, page_count, metadata)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        doc_id,
        doc_content.filename,
        doc_content.file_hash,
        doc_content.page_count,
        '{}',
    )

    chunks = split_document(doc_content, settings.chunk_size, settings.chunk_overlap)
    await embed_chunks(chunks, doc_id)

    return IngestResponse(
        document_id=str(doc_id),
        filename=doc_content.filename,
        page_count=doc_content.page_count,
        chunk_count=len(chunks),
        status="done",
    )


@router.get("/{document_id}/status", response_model=IngestStatusResponse)
async def get_ingest_status(document_id: str) -> IngestStatusResponse:
    """Get the ingestion status for a document.

    Args:
        document_id: UUID string of the document.

    Returns:
        IngestStatusResponse with current status and chunk count.

    Raises:
        HTTPException 404: If no document with that ID exists.
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")

    rows = await execute_query(
        "SELECT id, filename FROM documents WHERE id = $1",
        doc_uuid,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_rows = await execute_query(
        "SELECT COUNT(*) AS cnt FROM chunks WHERE document_id = $1",
        doc_uuid,
    )

    return IngestStatusResponse(
        document_id=document_id,
        filename=rows[0]["filename"],
        status="done",
        chunk_count=int(chunk_rows[0]["cnt"]),
    )
