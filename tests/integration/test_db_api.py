"""Integration tests against live PostgreSQL (pgvector)."""

from __future__ import annotations

import os
import uuid

import pytest

from src.extraction.service import load_document_for_extraction
from src.retrieval.vector_store import similarity_search
from tests.integration.conftest import insert_test_document

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"),
        reason="Set RUN_INTEGRATION_TESTS=1 with a live DATABASE_URL",
    ),
]


@pytest.mark.asyncio
async def test_health_reports_database_ok(integration_client) -> None:
    response = await integration_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


@pytest.mark.asyncio
async def test_documents_api_lists_and_loads_detail(integration_client, db_session) -> None:
    doc_id = await insert_test_document(
        filename="intake_form.pdf",
        pages=["Page one content", "Page two with HCPCS E1390"],
    )

    list_response = await integration_client.get("/documents/")
    assert list_response.status_code == 200
    docs = list_response.json()
    assert len(docs) == 1
    assert docs[0]["id"] == str(doc_id)
    assert docs[0]["filename"] == "intake_form.pdf"
    assert docs[0]["chunk_count"] == 2

    detail_response = await integration_client.get(f"/documents/{doc_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["page_count"] == 2
    assert len(detail["chunks"]) == 2
    assert "E1390" in detail["chunks"][1]["content"]


@pytest.mark.asyncio
async def test_similarity_search_returns_seeded_chunk(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedding = [0.0] * 1536
    embedding[0] = 1.0
    doc_id = await insert_test_document(embedding=embedding)

    monkeypatch.setattr("src.retrieval.vector_store.embed_query", lambda _query: embedding)

    results = await similarity_search(
        "oxygen concentrator",
        top_k=5,
        threshold=0.5,
        document_id=doc_id,
    )

    assert len(results) == 1
    assert results[0].document_id == doc_id
    assert results[0].similarity_score >= 0.99


@pytest.mark.asyncio
async def test_load_document_for_extraction_groups_pages(db_session) -> None:
    doc_id = await insert_test_document(
        pages=["[PAGE 1] intake", "[PAGE 2] procedure note with E1390"],
    )

    filename, pages = await load_document_for_extraction(doc_id)

    assert filename == "prior_auth.pdf"
    assert len(pages) == 2
    assert "intake" in pages[0]
    assert "E1390" in pages[1]


@pytest.mark.asyncio
async def test_get_document_returns_404_for_unknown_id(integration_client, db_session) -> None:
    missing_id = uuid.uuid4()
    response = await integration_client.get(f"/documents/{missing_id}")
    assert response.status_code == 404
