"""FastAPI endpoint smoke tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(api_client) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "langchain-document-pipeline"


@pytest.mark.asyncio
async def test_extract_invalid_document_id(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.api.extract.settings.anthropic_api_key", "test-key")
    response = await api_client.post(
        "/extract/",
        json={"document_id": "not-a-uuid", "chains": ["hcpcs"]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_extract_returns_structured_entities(
    api_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.extraction.entities import ExtractionResult, HCPCSCode

    doc_id = "550e8400-e29b-41d4-a716-446655440000"

    async def fake_extract(document_id, chains=None):
        return (
            ExtractionResult(
                document_id=str(document_id),
                hcpcs_codes=[HCPCSCode(code="E1390", description="Oxygen concentrator")],
                patient=None,
                input_tokens=120,
                output_tokens=45,
            ),
            ["sample warning"],
        )

    monkeypatch.setattr("src.api.extract.settings.anthropic_api_key", "test-key")
    monkeypatch.setattr("src.api.extract.extract_from_document", fake_extract)

    response = await api_client.post(
        "/extract/",
        json={"document_id": doc_id, "chains": ["hcpcs"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert len(data["hcpcs_codes"]) == 1
    assert data["hcpcs_codes"][0]["code"] == "E1390"
    assert data["warnings"] == ["sample warning"]
    assert data["input_tokens"] == 120


@pytest.mark.asyncio
async def test_dashboard_html(api_client) -> None:
    response = await api_client.get("/")
    assert response.status_code == 200
    assert "Document Pipeline" in response.text
