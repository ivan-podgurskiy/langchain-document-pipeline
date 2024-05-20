"""Orchestration pipeline: load → split → embed → store with async task queue."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from src.config import settings
from src.db.connection import execute_command, execute_query
from src.ingestion.embedder import embed_chunks
from src.ingestion.pdf_loader import DocumentContent, load_pdf_bytes
from src.ingestion.splitter import split_document


class IngestionStatus(str, Enum):
    """Possible states for an ingestion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class IngestionJob:
    """Represents an asynchronous ingestion task."""

    job_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    status: IngestionStatus
    chunk_count: int = 0
    error_message: str | None = None


# In-memory job registry (per process; for production use Redis or DB-backed jobs)
_jobs: dict[uuid.UUID, IngestionJob] = {}
_queue: asyncio.Queue = asyncio.Queue()
_worker_task: asyncio.Task | None = None


async def enqueue_ingestion(content: bytes, filename: str) -> IngestionJob:
    """Add a PDF ingestion task to the async queue.

    Creates a job record and returns immediately; the actual ingestion
    runs in the background worker coroutine.

    Args:
        content: Raw PDF bytes.
        filename: Original filename for display and deduplication.

    Returns:
        IngestionJob with PENDING status and assigned IDs.
    """
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    job = IngestionJob(
        job_id=job_id,
        document_id=doc_id,
        filename=filename,
        status=IngestionStatus.PENDING,
    )
    _jobs[job_id] = job

    await _queue.put((job, content))
    return job


def get_job(job_id: uuid.UUID) -> IngestionJob | None:
    """Retrieve an ingestion job by its ID.

    Args:
        job_id: UUID of the job to look up.

    Returns:
        IngestionJob if found, None otherwise.
    """
    return _jobs.get(job_id)


async def _process_job(job: IngestionJob, content: bytes) -> None:
    """Process a single ingestion job: load, split, embed, store.

    Args:
        job: The IngestionJob to process.
        content: Raw PDF bytes.
    """
    job.status = IngestionStatus.PROCESSING
    try:
        doc_content = load_pdf_bytes(content, job.filename)

        await execute_command(
            """
            INSERT INTO documents (id, filename, file_hash, page_count, metadata)
            VALUES ($1, $2, $3, $4, '{}')
            ON CONFLICT (file_hash) DO NOTHING
            """,
            job.document_id,
            doc_content.filename,
            doc_content.file_hash,
            doc_content.page_count,
        )

        chunks = split_document(doc_content, settings.chunk_size, settings.chunk_overlap)
        await embed_chunks(chunks, job.document_id)

        job.chunk_count = len(chunks)
        job.status = IngestionStatus.DONE
    except Exception as exc:
        job.status = IngestionStatus.FAILED
        job.error_message = str(exc)


async def _worker() -> None:
    """Background worker that drains the ingestion queue continuously."""
    while True:
        job, content = await _queue.get()
        await _process_job(job, content)
        _queue.task_done()


async def start_worker() -> None:
    """Start the background ingestion worker task.

    Should be called once on application startup (e.g. from FastAPI startup event).
    """
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker())
