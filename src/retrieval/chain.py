"""Retrieval QA chain combining vector search with Claude for answer generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from langchain.chains import RetrievalQA
from langchain_anthropic import ChatAnthropic

from src.config import settings
from src.retrieval.vector_store import SearchResult, similarity_search


@dataclass
class QueryResult:
    """Result of a retrieval-augmented query."""

    question: str
    answer: str
    source_chunks: list[SearchResult]
    model: str
    tokens_used: dict[str, int]


def build_qa_chain(
    model: str | None = None,
    temperature: float | None = None,
) -> ChatAnthropic:
    """Build a Claude LLM instance for answer generation.

    Args:
        model: Claude model identifier string. Defaults to settings value.
        temperature: Sampling temperature (0–1). Defaults to settings value.

    Returns:
        Configured ChatAnthropic instance.
    """
    return ChatAnthropic(
        model=model or settings.llm_model,
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        anthropic_api_key=settings.anthropic_api_key,
    )


SYSTEM_PROMPT = """You are a medical document analyst. You answer questions using only
information from the provided context. If the context does not contain enough information
to answer, say so explicitly. Do not speculate or add information not present in the context.

Always cite the relevant sections or page numbers when available."""


def format_context(chunks: list[SearchResult]) -> str:
    """Format search results into a context string for the LLM.

    Args:
        chunks: Ranked search results from vector store.

    Returns:
        Formatted context string with page references.
    """
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Chunk {i} | Page {chunk.page_number} | Similarity: {chunk.similarity_score:.2f}]\n"
            f"{chunk.content}"
        )
    return "\n\n---\n\n".join(parts)


async def answer_question(
    question: str,
    document_id: uuid.UUID | None = None,
    top_k: int | None = None,
    threshold: float | None = None,
    llm: ChatAnthropic | None = None,
) -> QueryResult:
    """Answer a question using retrieval-augmented generation.

    Retrieves relevant chunks from the vector store, formats them as context,
    and uses Claude to generate a grounded answer.

    Args:
        question: Natural language question to answer.
        document_id: Optional UUID to restrict retrieval to one document.
        top_k: Maximum chunks to retrieve. Defaults to settings value.
        threshold: Minimum similarity score. Defaults to settings value.
        llm: Optional pre-built LLM; created fresh if None.

    Returns:
        QueryResult with answer, source chunks, and token usage.
    """
    chunks = await similarity_search(
        query=question,
        top_k=top_k,
        threshold=threshold,
        document_id=document_id,
    )

    if not chunks:
        return QueryResult(
            question=question,
            answer="No relevant documents found to answer this question.",
            source_chunks=[],
            model=settings.llm_model,
            tokens_used={"input_tokens": 0, "output_tokens": 0},
        )

    context = format_context(chunks)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        f"ANSWER:"
    )

    if llm is None:
        llm = build_qa_chain()

    response = llm.invoke(prompt)
    answer = response.content
    usage = getattr(response, "usage_metadata", {}) or {}

    return QueryResult(
        question=question,
        answer=str(answer),
        source_chunks=chunks,
        model=settings.llm_model,
        tokens_used={
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
        },
    )
