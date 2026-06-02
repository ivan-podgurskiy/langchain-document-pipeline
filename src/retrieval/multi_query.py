"""Multi-query retriever: generate query variants to improve recall."""

from __future__ import annotations

import uuid

from langchain_anthropic import ChatAnthropic

from src.config import settings
from src.retrieval.vector_store import SearchResult, similarity_search

QUERY_EXPANSION_PROMPT = """You are a medical document search expert. Given a user question,
generate {num_variants} different search queries that would help find relevant information
in clinical documents (progress notes, prior authorizations, lab results, intake forms).

Each variant should rephrase the question using different medical terminology or perspective.
Return ONLY the queries, one per line, no numbering or labels.

Original question: {question}

Generate {num_variants} query variants:"""


def build_query_expander(model: str | None = None) -> ChatAnthropic:
    """Build an LLM instance for query expansion.

    Uses a slightly higher temperature for query diversity.

    Args:
        model: Claude model string. Defaults to settings value.

    Returns:
        ChatAnthropic instance configured for query expansion.
    """
    return ChatAnthropic(
        model=model or settings.llm_model,
        temperature=0.3,
        max_tokens=512,
        anthropic_api_key=settings.anthropic_api_key,
    )


def expand_query(
    question: str,
    num_variants: int = 3,
    llm: ChatAnthropic | None = None,
) -> list[str]:
    """Generate multiple query variants from a single question.

    Args:
        question: Original user question.
        num_variants: Number of alternative queries to generate.
        llm: Optional pre-built LLM; created fresh if None.

    Returns:
        List of query strings including the original question.
    """
    if llm is None:
        llm = build_query_expander()

    prompt = QUERY_EXPANSION_PROMPT.format(
        question=question,
        num_variants=num_variants,
    )

    response = llm.invoke(prompt)
    raw = response.content.strip()
    variants = [line.strip() for line in raw.splitlines() if line.strip()]
    # Include the original to guarantee at least one meaningful query
    all_queries = [question] + variants[:num_variants]
    return all_queries


def deduplicate_results(results_lists: list[list[SearchResult]]) -> list[SearchResult]:
    """Merge and deduplicate search results from multiple queries.

    Keeps the highest similarity score when the same chunk appears
    in results from different query variants.

    Args:
        results_lists: One list of SearchResult per query variant.

    Returns:
        Deduplicated, re-ranked list of SearchResult objects.
    """
    seen: dict[uuid.UUID, SearchResult] = {}
    for results in results_lists:
        for result in results:
            if result.chunk_id not in seen:
                seen[result.chunk_id] = result
            else:
                # Keep the higher similarity score
                if result.similarity_score > seen[result.chunk_id].similarity_score:
                    seen[result.chunk_id] = result

    return sorted(seen.values(), key=lambda r: r.similarity_score, reverse=True)


async def multi_query_search(
    question: str,
    num_variants: int = 3,
    top_k: int | None = None,
    threshold: float | None = None,
    document_id: uuid.UUID | None = None,
    llm: ChatAnthropic | None = None,
) -> list[SearchResult]:
    """Retrieve chunks using multiple query variants for improved recall.

    Expands the original question into several variants, runs similarity
    search for each, and returns a deduplicated, re-ranked result set.

    Args:
        question: The original user question.
        num_variants: Number of additional query variants to generate.
        top_k: Max chunks per query variant.
        threshold: Minimum similarity score per query variant.
        document_id: Optional UUID to restrict search scope.
        llm: Optional pre-built LLM for query expansion.

    Returns:
        Deduplicated SearchResult list ranked by similarity.
    """
    queries = expand_query(question, num_variants, llm)

    results_lists = []
    for q in queries:
        results = await similarity_search(
            query=q,
            top_k=top_k,
            threshold=threshold,
            document_id=document_id,
        )
        results_lists.append(results)

    return deduplicate_results(results_lists)
