"""Tests for retrieval helpers and QA chain."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from src.retrieval.chain import answer_question
from src.retrieval.multi_query import deduplicate_results
from src.retrieval.vector_store import SearchResult


def _make_result(chunk_id: uuid.UUID, score: float) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        content=f"chunk-{chunk_id}",
        page_number=1,
        similarity_score=score,
        metadata={},
    )


def test_deduplicate_results_keeps_highest_similarity() -> None:
    chunk_id = uuid.uuid4()
    low = _make_result(chunk_id, 0.71)
    high = _make_result(chunk_id, 0.93)
    other = _make_result(uuid.uuid4(), 0.88)

    merged = deduplicate_results([[low], [high, other]])

    assert len(merged) == 2
    assert merged[0].chunk_id == chunk_id
    assert merged[0].similarity_score == 0.93
    assert merged[1].similarity_score == 0.88


@pytest.mark.asyncio
async def test_answer_question_uses_multi_query_path(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_result(uuid.uuid4(), 0.9)
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content="Grounded answer",
        usage_metadata={"input_tokens": 100, "output_tokens": 20},
    )

    async def fake_multi_query_search(
        **kwargs: object,
    ) -> tuple[list[SearchResult], dict[str, int]]:
        return [chunk], {"input_tokens": 50, "output_tokens": 10}

    monkeypatch.setattr("src.retrieval.chain.multi_query_search", fake_multi_query_search)
    monkeypatch.setattr("src.retrieval.chain.tracker.record", lambda **_kwargs: None)

    result = await answer_question(
        "What HCPCS codes are ordered?", use_multi_query=True, llm=mock_llm
    )

    assert result.multi_query is True
    assert result.answer == "Grounded answer"
    assert result.tokens_used["input_tokens"] == 150
    assert result.tokens_used["output_tokens"] == 30
    assert len(result.source_chunks) == 1


@pytest.mark.asyncio
async def test_answer_question_uses_single_query_path(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_result(uuid.uuid4(), 0.85)
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content="Single-query answer",
        usage_metadata={"input_tokens": 80, "output_tokens": 15},
    )

    async def fake_similarity_search(**kwargs: object) -> list[SearchResult]:
        return [chunk]

    monkeypatch.setattr("src.retrieval.chain.similarity_search", fake_similarity_search)
    monkeypatch.setattr("src.retrieval.chain.tracker.record", lambda **_kwargs: None)

    result = await answer_question("What is the diagnosis?", use_multi_query=False, llm=mock_llm)

    assert result.multi_query is False
    assert result.tokens_used["input_tokens"] == 80
    assert result.answer == "Single-query answer"
