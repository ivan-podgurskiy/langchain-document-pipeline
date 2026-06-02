"""POST /query endpoint: natural language search over ingested documents."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.retrieval.chain import QueryResult, answer_question

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""

    question: str = Field(..., min_length=3, description="Natural language question")
    document_id: Optional[str] = Field(None, description="Restrict search to one document UUID")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Max chunks to retrieve")
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")


class SourceChunkResponse(BaseModel):
    """A source chunk included in the query response."""

    chunk_id: str
    document_id: str
    page_number: int
    similarity_score: float
    content: str


class QueryResponse(BaseModel):
    """Response body for the /query endpoint."""

    question: str
    answer: str
    sources: list[SourceChunkResponse]
    model: str
    input_tokens: int
    output_tokens: int


@router.post("/", response_model=QueryResponse)
async def query_documents(request: QueryRequest) -> QueryResponse:
    """Search documents and generate a grounded answer using RAG.

    Retrieves the most relevant chunks via HNSW similarity search,
    then asks Claude to produce an answer grounded in those chunks.

    Args:
        request: QueryRequest containing the question and optional filters.

    Returns:
        QueryResponse with the LLM answer and ranked source chunks.

    Raises:
        HTTPException 400: If document_id is provided but not a valid UUID.
    """
    doc_uuid: uuid.UUID | None = None
    if request.document_id:
        try:
            doc_uuid = uuid.UUID(request.document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_id format")

    result: QueryResult = await answer_question(
        question=request.question,
        document_id=doc_uuid,
        top_k=request.top_k,
        threshold=request.threshold,
    )

    return QueryResponse(
        question=result.question,
        answer=result.answer,
        sources=[
            SourceChunkResponse(
                chunk_id=str(chunk.chunk_id),
                document_id=str(chunk.document_id),
                page_number=chunk.page_number,
                similarity_score=round(chunk.similarity_score, 4),
                content=chunk.content[:500],
            )
            for chunk in result.source_chunks
        ],
        model=result.model,
        input_tokens=result.tokens_used.get("input_tokens", 0),
        output_tokens=result.tokens_used.get("output_tokens", 0),
    )
